from dataclasses import dataclass
from datetime import date


@dataclass
class Video:
    video_id: str
    title: str
    channel: str
    channel_id: str
    duration_sec: int
    published_at: date
    url: str
    views: int
    likes: int
    comments: int
