#!/usr/bin/env python3

import os
import unittest
from urllib.parse import urljoin

import requests
import retry

HH_API_ENDPOINT = 'https://api.hh.ru/'

# NOTE: this is the decorator that retries the failed tests
# It is needed because some tests may have a false negative result -
# there may be a fail when we expect to get less values due to filtering,
# but we actually get more because the users have added more new vacancies
# after the previous request than the number of filtered out vacancies.
# That is why we use this decorator to reduce false negatives and build trust
# for our tests.
# Note however that due to the same reasons, the tests may not detect the
# failure 100% of times (i.e. there may be a false positive result).
# This may happen if for example the API works incorrectly, but this
# effect is eliminated by users that add/remove vacancies between
# our requests. We could not get rid of it unless we would have
# our own database and our own API so that we could fully control
# the expected number of vacancies. (Or at least our own employer
# registered so that we would fully control its vacancies and test
# only on them)
# 5 is just some random picked number
retriable_test = retry.retry(exceptions=AssertionError, tries=5)


class TestHHAPIVacanciesTextBase(unittest.TestCase):

    def setUp(self):
        self.api_key = os.environ['HH_API_KEY']

    def _do_vacancies_request(self, text_param, custom_headers=None, custom_params=None):
        headers = {'Authorization': 'Bearer %s' % self.api_key}
        if custom_headers:
            headers.update(custom_headers)

        params = {'text': text_param}
        if custom_params:
            params.update(custom_params)

        url = urljoin(HH_API_ENDPOINT, 'vacancies')
        resp = requests.get(url, headers=headers, params=params)
        return resp.status_code, resp.json()


class TestEncoding(TestHHAPIVacanciesTextBase):

    def test_valid_text(self):
        code, resp = self._do_vacancies_request('test')
        self.assertEqual(code, 200)

    def test_null_byte(self):
        code, resp = self._do_vacancies_request('\x00')
        self.assertEqual(code, 200)

    def test_unicode(self):
        code, resp = self._do_vacancies_request('ਣ')
        self.assertEqual(code, 200)


class TestHeaders(TestHHAPIVacanciesTextBase):

    def test_invalid_auth(self):
        headers = {'Authorization': 'invalid'}
        code, resp = self._do_vacancies_request('test', custom_headers=headers)
        self.assertEqual(code, 403)

    def test_non_json_content_type_ignored(self):
        headers = {'Accept': 'application/x-www-form-urlencoded'}
        code, resp = self._do_vacancies_request('test', custom_headers=headers)
        self.assertEqual(code, 200)


class TestParams(TestHHAPIVacanciesTextBase):

    def test_pagination(self):
        params = {'page': 0, 'per_page': 1}
        code, resp = self._do_vacancies_request('test', custom_params=params)
        self.assertEqual(code, 200)
        self.assertEqual(resp['per_page'], 1)
        self.assertEqual(len(resp['items']), 1)
        self.assertEqual(resp['page'], 0)

    def test_too_big_pagination(self):
        params = {'page': 0, 'per_page': 1000}
        code, resp = self._do_vacancies_request('test', custom_params=params)
        self.assertEqual(code, 400)

    def test_too_deep_pagination(self):
        params = {'page': 2000, 'per_page': 10}
        code, resp = self._do_vacancies_request('test', custom_params=params)
        self.assertEqual(code, 400)

    @retriable_test
    def test_host_does_not_reduce_results(self):
        code, resp = self._do_vacancies_request('test')
        self.assertEqual(code, 200)
        default_host_n_results = resp['found']

        custom_host = {'host': 'headhunter.ge'}
        code, resp = self._do_vacancies_request('test', custom_params=custom_host)
        self.assertEqual(code, 200)
        custom_host_n_results = resp['found']
        self.assertGreaterEqual(custom_host_n_results, default_host_n_results)


class TestTextQuery(TestHHAPIVacanciesTextBase):

    @retriable_test
    def test_fixed_word_order(self):
        code, resp = self._do_vacancies_request('Продажа оборудования')
        self.assertEqual(code, 200)
        base_n = resp['found']

        code, resp = self._do_vacancies_request('"Продажа оборудования"')
        self.assertEqual(code, 200)
        quoted_n = resp['found']
        self.assertGreaterEqual(base_n, quoted_n)

    @retriable_test
    def test_fixed_word_form(self):
        code, resp = self._do_vacancies_request('Продажи')
        self.assertEqual(code, 200)
        base_n = resp['found']

        code, resp = self._do_vacancies_request('!Продажи')
        self.assertEqual(code, 200)
        fixed_word_form_n = resp['found']
        self.assertGreaterEqual(base_n, fixed_word_form_n)

    @retriable_test
    def test_wildcard(self):
        code, resp = self._do_vacancies_request('Гео*')
        self.assertEqual(code, 200)
        wildcard_n = resp['found']

        code, resp = self._do_vacancies_request('Геолог')
        self.assertEqual(code, 200)
        fixed_word_n = resp['found']
        self.assertGreaterEqual(wildcard_n, fixed_word_n)

    @retriable_test
    def test_synonyms(self):
        code, resp = self._do_vacancies_request('pr-менеджер')
        self.assertEqual(code, 200)
        with_synonyms_n = resp['found']

        code, resp = self._do_vacancies_request('pr-менеджер AND NOT !pr-manager')
        self.assertEqual(code, 200)
        no_synonym_n = resp['found']
        self.assertGreaterEqual(with_synonyms_n, no_synonym_n)

    @retriable_test
    def test_or(self):
        code, resp = self._do_vacancies_request('нефть OR бензин')
        self.assertEqual(code, 200)
        with_or_n = resp['found']

        code, resp = self._do_vacancies_request('нефть')
        self.assertEqual(code, 200)
        no_or_n = resp['found']
        self.assertGreaterEqual(with_or_n, no_or_n)

    @retriable_test
    def test_and(self):
        code, resp = self._do_vacancies_request('"холодильное оборудование"')
        self.assertEqual(code, 200)
        no_and_n = resp['found']

        code, resp = self._do_vacancies_request('"холодильное оборудование" AND "торговое оборудование"')
        self.assertEqual(code, 200)
        with_and_n = resp['found']
        self.assertGreaterEqual(no_and_n, with_and_n)

    @retriable_test
    def test_not(self):
        code, resp = self._do_vacancies_request('cola')
        self.assertEqual(code, 200)
        no_not_n = resp['found']

        code, resp = self._do_vacancies_request('cola NOT pepsi')
        self.assertEqual(code, 200)
        with_not_n = resp['found']
        self.assertGreaterEqual(no_not_n, with_not_n)

    @retriable_test
    def test_complex_condition(self):
        code, resp = self._do_vacancies_request('продажи AND алкоголь')
        self.assertEqual(code, 200)
        base_n = resp['found']

        code, resp = self._do_vacancies_request('sales AND alcohol')
        self.assertEqual(code, 200)
        base_eng_n = resp['found']

        code, resp = self._do_vacancies_request('продажи OR sales')
        self.assertEqual(code, 200)
        first_clause_n = resp['found']

        code, resp = self._do_vacancies_request('алкоголь OR alcohol')
        self.assertEqual(code, 200)
        second_clause_n = resp['found']

        code, resp = self._do_vacancies_request('(продажи OR sales) AND (алкоголь OR alcohol)')
        self.assertEqual(code, 200)
        complex_n = resp['found']

        self.assertGreaterEqual(complex_n, base_n)
        self.assertGreaterEqual(complex_n, base_eng_n)

        self.assertGreaterEqual(first_clause_n, complex_n)
        self.assertGreaterEqual(second_clause_n, complex_n)

    @retriable_test
    def test_field_search(self):
        code, resp = self._do_vacancies_request('python OR java')
        self.assertEqual(code, 200)
        all_fields_n = resp['found']

        code, resp = self._do_vacancies_request('NAME:(python or java)')
        self.assertEqual(code, 200)
        name_field_n = resp['found']
        self.assertGreaterEqual(all_fields_n, name_field_n)


if __name__ == '__main__':
    import logging
    logging.basicConfig()
    unittest.main()
