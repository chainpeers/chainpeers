from sqlalchemy import Column, Integer, String, JSON, BOOLEAN
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
Base = declarative_base()


class Peer(Base):
    __tablename__ = "peer"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    version = Column(String, index=True)
    time = Column(String, index=True)
    score = Column(String, index=True)

    is_starting = Column(BOOLEAN, index=True, default=False)


class Slice(Base):
    __tablename__ = "slice"

    id = Column(Integer, primary_key=True, index=True)
    is_open = Column(BOOLEAN, index=True)
    chain_name = Column(String, index=True)
    time = Column(String, index=True)
    starting_peers = Column(JSON, index=True)


class SliceResults(Base):
    __tablename__ = 'slice results'

    id = Column(Integer, primary_key=True, index=True)
    slice_id = Column(Integer, index=True)
    peer_ids = Column(JSON, index=True)

