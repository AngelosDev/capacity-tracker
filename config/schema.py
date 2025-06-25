# config/schema.py
from dataclasses import dataclass

@dataclass
class IssueSchema:
    Project: str
    Key: str
    Updated: str
    Updated_YearMonth: str
    Created: str
    Summary: str
    Description: str
    Issue_Type: str
    Status: str
    Resolution: str
    Resolved_YearMonth: str
    Assignee: str
    Category: str
