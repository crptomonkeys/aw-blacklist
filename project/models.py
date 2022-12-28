from sqlmodel import SQLModel, Field

class BlacklistBase(SQLModel):
    wallet: str
    added: str
    reason: str

class Blacklist(BlacklistBase, table=True):
    id: int = Field(default=None, primary_key=True)


class BlacklistCreate(BlacklistBase):
    pass

