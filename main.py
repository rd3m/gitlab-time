import os
import click
from gitlab import Gitlab
from dotenv import load_dotenv
from datetime import datetime, time, timedelta
from collections import defaultdict
import pytz
import calendar


load_dotenv()

sydney_tz = pytz.timezone("Australia/Sydney")


def localize_to_sydney(dt):
    """Localize a naive datetime object to the Sydney timezone."""
    if dt.tzinfo is None:
        return sydney_tz.localize(dt)
    return dt.astimezone(sydney_tz)


def work_time_between(start, end):
    """Calculate total work time for each day between start and end datetimes."""
    day_hours = defaultdict(lambda: timedelta())

    start = localize_to_sydney(start)
    end = localize_to_sydney(end)
    current_day = start.date()

    while current_day <= end.date():
        if not is_weekday(current_day):
            current_day += timedelta(days=1)
            continue

        day_start = datetime.combine(current_day, time(9, 0))
        day_end = datetime.combine(current_day, time(17, 0))

        day_start = localize_to_sydney(day_start)
        day_end = localize_to_sydney(day_end)

        # Check if label was applied after work hours or removed before work hours
        if start > day_end or end < day_start:
            current_day += timedelta(days=1)
            continue

        # Adjust start and end time if they fall outside work hours on the current day
        if start.date() == current_day and start.time() < time(9, 0):
            start = day_start
        if end.date() == current_day and end.time() > time(17, 0):
            end = day_end

        time_with_label = min(day_end, end) - max(day_start, start)
        day_hours[current_day.strftime("%A")] += time_with_label

        current_day += timedelta(days=1)

    return day_hours


def is_weekday(dt):
    """Return True if dt is a weekday."""
    return dt.weekday() < 5


def adjust_start_time(dt):
    """Adjust start time to fit within working hours."""
    nine_am = time(9, 0)
    five_pm = time(17, 0)

    if dt.time() > five_pm or not is_weekday(dt):
        # If it's after 5pm or a weekend, move to 9am of next weekday
        dt += timedelta(days=1)
        while not is_weekday(dt):
            dt += timedelta(days=1)
        return localize_to_sydney(datetime.combine(dt.date(), nine_am))

    elif dt.time() < nine_am:
        # If it's before 9am, set to 9am of the same day
        return localize_to_sydney(datetime.combine(dt.date(), nine_am))

    return dt


def adjust_end_time(dt):
    """Adjust end time to fit within working hours."""
    nine_am = time(9, 0)
    five_pm = time(17, 0)
    if not is_weekday(dt) or dt.time() < nine_am:
        # If it's a weekend or before 9am, move to 5pm of previous weekday
        while not is_weekday(dt):
            dt -= timedelta(days=1)
        return datetime.combine(dt.date(), five_pm)
    elif dt.time() > five_pm:
        # If it's after 5pm, set to 5pm of the same day
        return datetime.combine(dt.date(), five_pm)
    return dt


@click.command()
@click.option(
    "-p", "--project-id", required=True, help="The project id (e.g., 38062628)"
)
@click.option("-i", "--issue-number", required=True, type=int, help="The issue number")
def main(project_id, issue_number):
    """Calculates how long a 'Doing' label was on a GitLab issue"""

    token = os.getenv("GITLAB_TOKEN")
    group_id = os.getenv("GITLAB_GROUP_ID")

    if not all([token, group_id]):
        missing_vars = []
        if not token:
            missing_vars.append("GITLAB_TOKEN")
        if not group_id:
            missing_vars.append("GITLAB_GROUP")
        print(f"Error: Missing environment variable(s): {', '.join(missing_vars)}.")
        return

    client = Gitlab(private_token=token)
    project = client.projects.get(project_id)
    issue = project.issues.get(issue_number)
    label_name = "Doing"

    events = issue.resourcelabelevents.list()

    total_hours = defaultdict(lambda: timedelta())
    label_start_time = None

    for event in events:
        event_time = (
            datetime.fromisoformat(event.created_at.replace("Z", ""))
            .replace(tzinfo=pytz.utc)
            .astimezone(sydney_tz)
        )

        if event.label["name"] == label_name and event.action == "add":
            label_start_time = event_time

        elif (
            event.label["name"] == label_name
            and event.action == "remove"
            and label_start_time
        ):
            for day, duration in work_time_between(
                label_start_time, event_time
            ).items():
                total_hours[day] += duration
            label_start_time = None

    if label_start_time:  # If label was added and never removed till now
        for day, duration in work_time_between(
            label_start_time, datetime.utcnow().astimezone(sydney_tz)
        ).items():
            total_hours[day] += duration

    print("Day       | Hours")
    print("-----------------")
    day_order = {day: i for i, day in enumerate(calendar.day_name)}
    for day, duration in sorted(total_hours.items(), key=lambda x: day_order[x[0]]):
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes = remainder // 60
        print(f"{day:<9} | {int(hours)}h {int(minutes)}m")


if __name__ == "__main__":
    main()
