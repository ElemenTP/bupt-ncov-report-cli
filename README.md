# BUPT 2019-nCoV Report Bot
## Requirements

- Python3 (dev with 3.10.4)
- pip

Run `pip install -r requirements.txt` to install required components.

## Deployment

1. Copy `include/config.example.py` to `include/config.py`.
2. Run `python main.py --initdb` **once** to initialize SQLite database (my_app.db).
3. Run `python main.py` to start the bot. 

By default, the bot will checkin all the normal accounts at 0:10 *UTC+8*, and retry the failed ones at 0:25.
You can change this behavior in `include/config.py`.

## How it works

Following step are proceed when checkin. 

1. Extracts `oldInfo` and `def` from web page.
2. Replace `id`, `uid`, `date`, and `created` in `oldInfo` by the ones in `def`.
3. Sanitize these properties using default values:  
`ismoved`, `jhfjrq`, `jhfjjtgj`, `jhfjhbcc`, `sfxk`, `xkqq`, `sfsfbh`, `ismoved`, `xjzd`, `bztcyy`.
4. Pick `address`, `city`, `province`, `area` out from `geo_api_info` if they are empty.
5. Post final data to saving API.

## Contributing

Pull requests and issues are always welcome.

## Credit

Special thanks to [ipid/bupt-ncov-report](https://github.com/ipid/bupt-ncov-report).

## What does this fork do?

Remove tgbot interface, implement a simple command line interface.
