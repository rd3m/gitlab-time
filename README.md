# GitLab time reporting

A script that returns weekdays and the amount of time a GitLab issue had a "Doing" label applied.

## Assumptions

- 9am to 5pm is considered a workday and the maximum amount of time that can be logged in a day is 8 hours
- Weekends are excluded
- Timezone is AEDT (Australian Eastern Daylight Time)

## Setup

1. Set up a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a .env file in the project root with your GitLab token and Group ID:

```bash
GITLAB_TOKEN=your_gitlab_token
GITLAB_GROUP_ID=your_group_id
```

## Usage

```bash
python3 main.py -p PROJECT_ID -i ISSUE_NUMBER
```

## Example output

```bash
Day       | Hours
-----------------
Thursday  | 1h 35m
Friday    | 8h 0m
```

## Future improvements

- [ ] Add tests
- [ ] Add support for multiple issues
- [ ] Add support for multiple projects
- [ ] Add support for different timezones
