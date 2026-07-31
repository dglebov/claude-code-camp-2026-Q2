"""Port of `ruby/01_struct_skeleton/lib/boukensha/tasks/player.rb`."""

from .base import Base


class Player(Base):
    @classmethod
    def task_name(cls):
        return "player"
