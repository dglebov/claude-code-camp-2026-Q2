"""Port of `ruby/01_struct_skeleton/lib/boukensha/tasks/base.rb`.

Abstract and stateless: all behaviour is class methods taking a `settings` dict. No instances
are created. Concrete subclasses define `task_name`.
"""

import os


class Base:
    @classmethod
    def task_name(cls):
        raise NotImplementedError(f"{cls.__name__} must define .task_name")

    @classmethod
    def provider(cls, settings):
        value = cls._fetch(settings, "provider")
        if value is None:
            raise ValueError(f"tasks.{cls.task_name()}.provider is required in settings.yaml")
        return value

    @classmethod
    def model(cls, settings):
        value = cls._fetch(settings, "model")
        if value is None:
            raise ValueError(f"tasks.{cls.task_name()}.model is required in settings.yaml")
        return value

    @classmethod
    def prompt_override(cls, settings, prompt="system"):
        """Ruby's `prompt_override?`. Strict: only the literal boolean True enables an override."""
        node = cls._fetch(settings, "prompt_override")
        if not isinstance(node, dict):
            return False
        return node.get(str(prompt)) is True

    @classmethod
    def prompt(cls, settings, name="system", user_prompts_dir=None, default_prompts_dir=None):
        if cls.prompt_override(settings, name):
            text = cls._read_user_prompt(name, user_prompts_dir=user_prompts_dir)
            if text is not None:
                return text

        return cls._read_default_prompt(name, default_prompts_dir=default_prompts_dir)

    @classmethod
    def system_prompt(cls, settings, user_prompts_dir=None, default_prompts_dir=None):
        return cls.prompt(
            settings,
            "system",
            user_prompts_dir=user_prompts_dir,
            default_prompts_dir=default_prompts_dir,
        )

    # ---------- private ---------------------------------------------------

    @classmethod
    def _fetch(cls, settings, key):
        # Ruby raises NoMethodError when `settings` is nil. Returning None instead lets the
        # caller surface the far more useful "... is required in settings.yaml" message.
        if not isinstance(settings, dict):
            return None
        return settings.get(str(key))

    @classmethod
    def _read_user_prompt(cls, prompt_name, user_prompts_dir=None):
        if user_prompts_dir is None:
            return None

        return cls._read_file(os.path.join(user_prompts_dir, cls.task_name(), f"{prompt_name}.md"))

    @classmethod
    def _read_default_prompt(cls, prompt_name, default_prompts_dir=None):
        if default_prompts_dir is None:
            return None

        return cls._read_file(os.path.join(default_prompts_dir, f"{prompt_name}.md"))

    @staticmethod
    def _read_file(path):
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
