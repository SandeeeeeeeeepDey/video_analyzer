from .prompts import (
    HYGIENE_PROMPT,
    OCCUPANCY_PROMPT,
    QUEUE_LENGTH_PROMPT,
    CUSTOMER_BEHAVIOUR_PROMPT,
    OPERATIONAL_EFFICIENCY_PROMPT,
    STAFF_BEHAVIOUR_PROMPT,
    SAFETY_PROMPT,
    TIME_MONITORING_PROMPT,
    CUSTOMER_REQUIREMENTS_PROMPT,
    FOLLOWING_COOKING_STEPS_PROMPT,
)

PROMPT_TEMPLATES = {
    "hygiene": {
        "prompt": HYGIENE_PROMPT,
        "output_keys": [
            "UnhygienicPractices",
            "StaffHygieneStandards",
            "SurfaceAndUtensilCleanliness",
            "HandwashingPractices"
        ],
    },
    "occupancy": {
        "prompt": OCCUPANCY_PROMPT,
        "output_keys": [
            "OccupancyTimeline",
            "PeakOccupancy",
            "AverageOccupancy"
        ],

    },
    "queue_length": {
        "prompt": QUEUE_LENGTH_PROMPT,
        "output_keys": [
            "QueueTimeline",
            "PeakQueueLength",
            "AverageQueueLength"
        ],
    },
    "customer_behaviour": {
        "prompt": CUSTOMER_BEHAVIOUR_PROMPT,
        "output_keys": [
            "SatisfactionIndicators",
            "DissatisfactionIndicators",
            "UnusualActions"
        ],
    },
    "operational_efficiency": {
        "prompt": OPERATIONAL_EFFICIENCY_PROMPT,
        "output_keys": [
            "StoragePractices",
            "TimeSensitiveHandling",
            "WasteDisposal",
            "EquipmentAndWorkflow",
            "ServingAndReplenishment",
            "StaffCoordination"
        ],
    },
    "staff_behaviour": {
        "prompt": STAFF_BEHAVIOUR_PROMPT,
        "output_keys": [
            "SuspiciousActions",
            "CustomerInteraction",
            "ProfessionalConduct",
            "TeamworkAndCoordination",
            "RuleCompliance"
        ],
    },
    "safety": {
        "prompt": SAFETY_PROMPT,
        "output_keys": [
            "WorkplaceHazards",
            "EquipmentSafety",
            "FireAndElectricalSafety",
            "ProtectiveMeasures"
        ],
    },
    "time_monitering": {
        "prompt": TIME_MONITORING_PROMPT,
        "output_keys": [
            "TaskDurations",
            "Delays",
            "Inefficiencies"
        ],
    },
    "customer_requirements": {
        "prompt": CUSTOMER_REQUIREMENTS_PROMPT,
        "output_keys": [
            "VisibleRequests",
            "FoodPreferences",
            "FeedbackIndicators"
        ],
    },
    "following_cooking_steps": {
        "prompt": FOLLOWING_COOKING_STEPS_PROMPT,
        "output_keys": [
            "StepSequence",
            "StepOmissions",
            "StepDeviations"
        ],
    },
}