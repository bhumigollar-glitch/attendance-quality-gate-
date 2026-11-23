from typing import Dict, List, Optional
from app.rules.base import BaseRuleSet
from app.rules.versions.v1_0_0 import RuleSetV100
from app.rules.versions.v1_1_0 import RuleSetV110


class RuleRegistry:
    """Registry maintaining all versioned attendance rule sets."""

    def __init__(self) -> None:
        self._rule_sets: Dict[str, BaseRuleSet] = {}
        # Register rule sets
        self.register(RuleSetV100())
        self.register(RuleSetV110())

    def register(self, rule_set: BaseRuleSet) -> None:
        self._rule_sets[rule_set.version] = rule_set

    def get(self, version: str) -> Optional[BaseRuleSet]:
        return self._rule_sets.get(version)

    def list_versions(self) -> List[str]:
        return sorted(list(self._rule_sets.keys()))

    def get_all(self) -> Dict[str, BaseRuleSet]:
        return dict(self._rule_sets)


# Global singleton registry
rule_registry = RuleRegistry()
