"""Port of `ruby/07_the_run_dsl/lib/boukensha/tasks/player.rb`."""

from .base import Base


class Player(Base):
    @classmethod
    def task_name(cls):
        return "player"
