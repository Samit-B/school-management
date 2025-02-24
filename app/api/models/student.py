from pydantic import BaseModel

class Student(BaseModel):
    name: str
    student_id: str
    student_class: str
    dob: str
    gender: str
    city: str
    marks:int
# Pydantic Model for Event
class Event(BaseModel):
    title: str
    date: str
    description: str