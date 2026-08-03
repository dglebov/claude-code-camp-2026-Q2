"""Port of `ruby/05_agent_loop/lib/boukensha/tasks/player.rb`."""

from .base import Base


class Player(Base):
    @classmethod
    def task_name(cls):
        return "player"
