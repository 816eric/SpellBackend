from sqlmodel import SQLModel, Field


class UsageDay(SQLModel, table=True):
    """Seconds a signed-in user had the app open on one day (YYYY-MM-DD, UTC).

    Fed by the app's foreground heartbeat (POST /usage/heartbeat). Only the
    account name, the day and a counter are stored - no device id, IP address,
    location or screen content - and the rows are deleted with the account.
    Read by the admin dashboard only."""
    user_name: str = Field(primary_key=True)
    day: str = Field(primary_key=True)
    seconds: int = 0
