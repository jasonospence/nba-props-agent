from pydantic import BaseModel, Field
from typing import List, Optional

class Game(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    commence_time: str

class PropCandidate(BaseModel):
    game_id: str
    game_label: str
    player_name: str
    prop_type: str
    line: float
    over_price: Optional[int] = None
    under_price: Optional[int] = None
    bookmaker: Optional[str] = None

class PlayerRecentStatLine(BaseModel):
    game_id: str
    date: str
    team: str
    opponent: str
    minutes: float = 0
    points: float = 0
    rebounds: float = 0
    assists: float = 0
    threes: float = 0

class MissedGameInfo(BaseModel):
    game_id: str
    date: str
    reason: str = "unknown"

class ResearchRecord(BaseModel):
    game_label: str
    player_name: str
    prop_type: str
    line: float
    bookmaker: Optional[str] = None
    over_price: Optional[int] = None
    under_price: Optional[int] = None

    last_6_played_values: List[float] = Field(default_factory=list)
    last_6_minutes: List[float] = Field(default_factory=list)

    hit_rate_last_6: int = 0
    recent_average: float = 0
    recent_median: float = 0
    minutes_average: float = 0
    minutes_range: float = 0

    missed_recent_team_games: List[MissedGameInfo] = Field(default_factory=list)
    todays_injury_status: str = "unknown"
    todays_injury_note: str = ""

    confidence_score: float = 0
    reject: bool = False
    reject_reasons: List[str] = Field(default_factory=list)
    risk_notes: List[str] = Field(default_factory=list)