"""Port of `ruby/10_standard_tool_library/lib/boukensha/tasks/player.rb`."""

from .base import Base


class Player(Base):
    @classmethod
    def task_name(cls):
        return "player"
