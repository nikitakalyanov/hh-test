test hh.ru API

# run locally (python3 and pip required)

```bash
export HH_API_KEY='your-api-key'

pip install -r requirements.txt
./test_hh_api.py
```

# or in a venv (virtualenv python package required)
```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
export HH_API_KEY='your-api-key'
./test_hh_api.py
deactivate
```

# or in Docker
```
docker build --tag hh-api-test:1.0 .
docker run -d --name my-hh-api-test --env HH_API_KEY=your-api-key hh-api-test:1.0
# then you can check the test result with
docker logs my-hh-api-test
```
