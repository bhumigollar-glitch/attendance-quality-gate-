from typing import List
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.rules.registry import rule_registry
from app.schemas import RuleSetSchema, RuleVersionsResponse, RuleDefinitionSchema

router = APIRouter()


@router.get("/rules", response_model=RuleVersionsResponse, tags=["Rules"])
def get_all_rules():
    """
    Retrieve all available validation rule sets and their version specifications.
    """
    all_rule_sets = rule_registry.get_all()
    response_list: List[RuleSetSchema] = []

    for version, rset in sorted(all_rule_sets.items()):
        rules = [
            RuleDefinitionSchema(
                rule_id=r.rule_id,
                name=r.name,
                description=r.description,
                severity=r.severity.value if hasattr(r.severity, "value") else str(r.severity),
                category=r.category,
            )
            for r in rset.get_rules()
        ]
        response_list.append(
            RuleSetSchema(
                version=rset.version,
                name=rset.name,
                description=rset.description,
                required_columns=rset.required_columns,
                optional_columns=rset.optional_columns,
                permitted_statuses=sorted([s.title() for s in rset.permitted_statuses]),
                rules=rules,
            )
        )

    return RuleVersionsResponse(
        available_versions=rule_registry.list_versions(),
        default_version=settings.DEFAULT_RULE_VERSION,
        rule_sets=response_list,
    )


@router.get("/rules/{version}", response_model=RuleSetSchema, tags=["Rules"])
def get_rule_set_by_version(version: str):
    """
    Retrieve detailed specification of a specific rule set version.
    """
    rset = rule_registry.get(version)
    if not rset:
        raise HTTPException(
            status_code=404,
            detail=f"Rule set version '{version}' not found. Available versions: {', '.join(rule_registry.list_versions())}",
        )

    rules = [
        RuleDefinitionSchema(
            rule_id=r.rule_id,
            name=r.name,
            description=r.description,
            severity=r.severity.value if hasattr(r.severity, "value") else str(r.severity),
            category=r.category,
        )
        for r in rset.get_rules()
    ]

    return RuleSetSchema(
        version=rset.version,
        name=rset.name,
        description=rset.description,
        required_columns=rset.required_columns,
        optional_columns=rset.optional_columns,
        permitted_statuses=sorted([s.title() for s in rset.permitted_statuses]),
        rules=rules,
    )
