"""Port of `ruby/04_api_client/lib/boukensha/tasks/player.rb`."""

from .base import Base


class Player(Base):
    @classmethod
    def task_name(cls):
        return "player"
