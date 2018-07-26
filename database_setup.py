from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=True)
    picture = Column(String(250))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'username':     self.username,
            'id':           self.id,
            'email':        self.email
        }


class Manufacturer(Base):
    __tablename__ = 'manufacturer'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name':         self.name,
            'id':           self.id,
            'user_id':      self.user_id
        }


class Aircraft(Base):
    __tablename__ = 'aircraft'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    price = Column(String(8))
    range = Column(Integer)
    picture = Column(String(250))
    user_id = Column(Integer, ForeignKey('user.id'))
    manufacturer_id = Column(Integer, ForeignKey('manufacturer.id'))
    manufacturer = relationship(Manufacturer)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name':         self.name,
            'description':  self.description,
            'id':           self.id,
            'price':        self.price,
            'range':        self.range,
            'user_id':      self.user_id,
            'picture':      self.picture
        }


engine = create_engine('sqlite:///itemcatalog.db')

Base.metadata.create_all(engine)
