"""
SchedulerAgent - Converts allocations into monthly tasks and crop calendars.
Generates planting, management, and harvest schedules for Zimbabwe context.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from enum import Enum


class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskType(Enum):
    LAND_PREP = "land_preparation"
    PLANTING = "planting"
    FERTILIZING = "fertilizing"
    WEEDING = "weeding"
    PEST_CONTROL = "pest_control"
    IRRIGATION = "irrigation"
    HARVEST = "harvest"
    POST_HARVEST = "post_harvest"
    LIVESTOCK_FEEDING = "livestock_feeding"
    LIVESTOCK_HEALTH = "livestock_health"
    BREEDING = "breeding"
    MARKETING = "marketing"


@dataclass
class FarmTask:
    """A single scheduled task."""
    task_id: str
    task_type: TaskType
    enterprise: str
    month: int  # 1-12
    week: Optional[int]  # 1-4 within month
    description: str
    priority: TaskPriority
    labor_days: float
    inputs_required: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    agent_assignment: Optional[str] = None  # Which AgriMesh agent handles this
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "enterprise": self.enterprise,
            "month": self.month,
            "week": self.week,
            "description": self.description,
            "priority": self.priority.value,
            "labor_days": self.labor_days,
            "inputs_required": self.inputs_required,
            "dependencies": self.dependencies,
            "agent_assignment": self.agent_assignment,
        }


@dataclass
class CropCalendar:
    """Crop-specific calendar for a growing season."""
    crop: str
    area_ha: float
    planting_month: int
    harvest_month: int
    tasks: List[FarmTask] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop": self.crop,
            "area_ha": self.area_ha,
            "planting_month": self.planting_month,
            "harvest_month": self.harvest_month,
            "tasks": [t.to_dict() for t in self.tasks],
        }


@dataclass
class LivestockCalendar:
    """Livestock management calendar."""
    livestock: str
    count: int
    tasks: List[FarmTask] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "livestock": self.livestock,
            "count": self.count,
            "tasks": [t.to_dict() for t in self.tasks],
        }


MONTH_NAMES = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}


@dataclass
class FarmSchedule:
    """Complete farm schedule for a year."""
    year: int
    crop_calendars: List[CropCalendar]
    livestock_calendars: List[LivestockCalendar]
    monthly_summary: Dict[int, Dict[str, Any]]  # month -> summary
    total_labor_days: float
    peak_month: int
    peak_labor_days: float
    
    def _get_key_dates(self) -> Dict[str, Dict[str, str]]:
        """Extract planting and harvest windows from crop calendars."""
        planting = {}
        harvest = {}
        for cal in self.crop_calendars:
            planting[cal.crop] = MONTH_NAMES.get(cal.planting_month, str(cal.planting_month))
            harvest[cal.crop] = MONTH_NAMES.get(cal.harvest_month, str(cal.harvest_month))
        return {"planting": planting, "harvest": harvest}
    
    def _get_monthly_plans(self) -> List[Dict[str, Any]]:
        """Convert monthly summary to list format for frontend."""
        return [
            {"month": MONTH_NAMES.get(m, str(m)), "total_labor_days": data["labor_days"]}
            for m, data in sorted(self.monthly_summary.items())
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "key_dates": self._get_key_dates(),
            "monthly_plans": self._get_monthly_plans(),
            "crop_calendars": [c.to_dict() for c in self.crop_calendars],
            "livestock_calendars": [l.to_dict() for l in self.livestock_calendars],
            "monthly_summary": self.monthly_summary,
            "total_labor_days": self.total_labor_days,
            "peak_month": MONTH_NAMES.get(self.peak_month, str(self.peak_month)),
            "peak_labor_days": self.peak_labor_days,
        }
    
    def get_tasks_for_month(self, month: int) -> List[FarmTask]:
        """Get all tasks scheduled for a specific month."""
        tasks = []
        for cal in self.crop_calendars:
            tasks.extend([t for t in cal.tasks if t.month == month])
        for cal in self.livestock_calendars:
            tasks.extend([t for t in cal.tasks if t.month == month])
        return sorted(tasks, key=lambda t: (t.priority.value, t.week or 1))


# Zimbabwe crop calendars (month numbers: 1=Jan, 11=Nov, etc.)
# Based on typical summer rainfall pattern
CROP_CALENDARS_ZW = {
    "maize": {
        "land_prep": [10],  # October
        "planting": [11, 12],  # Nov-Dec (with rains)
        "fertilizing": [12, 1],
        "weeding": [12, 1, 2],
        "harvest": [4, 5],  # April-May
        "season_type": "summer",
    },
    "sorghum": {
        "land_prep": [10],
        "planting": [11, 12],
        "fertilizing": [12, 1],
        "weeding": [1, 2],
        "harvest": [5, 6],
        "season_type": "summer",
    },
    "groundnuts": {
        "land_prep": [10, 11],
        "planting": [11, 12],
        "fertilizing": [12],
        "weeding": [12, 1, 2],
        "harvest": [4, 5],
        "season_type": "summer",
    },
    "sunflower": {
        "land_prep": [10],
        "planting": [11, 12],
        "fertilizing": [12],
        "weeding": [12, 1],
        "harvest": [4, 5],
        "season_type": "summer",
    },
    "cotton": {
        "land_prep": [9, 10],
        "planting": [10, 11],
        "fertilizing": [11, 12, 1],
        "weeding": [11, 12, 1, 2],
        "pest_control": [12, 1, 2, 3],
        "harvest": [4, 5, 6],
        "season_type": "summer",
    },
    "tobacco": {
        "land_prep": [7, 8],  # Seedbed prep
        "planting": [9, 10],  # Transplanting
        "fertilizing": [10, 11, 12],
        "weeding": [10, 11, 12],
        "harvest": [1, 2, 3],  # Reaping
        "post_harvest": [2, 3, 4],  # Curing
        "season_type": "summer",
    },
    "vegetables": {
        "land_prep": [1, 4, 7, 10],  # Year-round with irrigation
        "planting": [1, 2, 4, 5, 7, 8, 10, 11],
        "fertilizing": [2, 3, 5, 6, 8, 9, 11, 12],
        "weeding": list(range(1, 13)),
        "irrigation": list(range(1, 13)),
        "harvest": [3, 4, 6, 7, 9, 10, 12, 1],
        "season_type": "year_round",
    },
    "fodder": {
        "land_prep": [9, 10],
        "planting": [10, 11],  # Or ratoon from previous
        "fertilizing": [11, 1, 3],
        "harvest": [1, 2, 3, 4, 5, 6],  # Multiple cuts
        "season_type": "perennial",
    },
}

# Livestock management calendars
LIVESTOCK_CALENDARS_ZW = {
    "cattle": {
        "breeding": [10, 11],  # To calve in wet season
        "vaccination": [9, 3],
        "dipping": list(range(1, 13)),  # Tick control
        "deworming": [4, 10],
        "weaning": [6, 7],
        "marketing": [8, 9, 10],  # Before rains
    },
    "goats": {
        "breeding": [3, 4, 9, 10],  # Twice yearly possible
        "vaccination": [3, 9],
        "deworming": [4, 10],
        "marketing": list(range(1, 13)),  # Year-round demand
    },
    "sheep": {
        "breeding": [3, 9],
        "shearing": [9, 10],  # Before summer
        "vaccination": [3, 9],
        "deworming": [4, 10],
    },
    "poultry": {
        "brooding": list(range(1, 13)),  # Continuous
        "vaccination": list(range(1, 13)),
        "marketing": list(range(1, 13)),
    },
    "pigs": {
        "breeding": [2, 3, 8, 9],
        "vaccination": [1, 7],
        "deworming": [3, 9],
        "marketing": [6, 7, 12, 1],
    },
}


class SchedulerAgent:
    """
    Agent for generating farm schedules from allocations.
    """
    
    def __init__(self, year: Optional[int] = None):
        self.year = year or datetime.now().year
        self._task_counter = 0
    
    def _next_task_id(self, prefix: str = "T") -> str:
        """Generate unique task ID."""
        self._task_counter += 1
        return f"{prefix}{self._task_counter:04d}"
    
    def generate_crop_calendar(
        self,
        crop: str,
        area_ha: float,
        zone: str,
    ) -> CropCalendar:
        """
        Generate crop calendar for a specific crop and area.
        """
        cal_data = CROP_CALENDARS_ZW.get(crop, {})
        tasks = []
        
        # Land preparation
        for month in cal_data.get("land_prep", [10]):
            tasks.append(FarmTask(
                task_id=self._next_task_id("LP"),
                task_type=TaskType.LAND_PREP,
                enterprise=crop,
                month=month,
                week=2,
                description=f"Prepare {area_ha:.1f} ha for {crop}: plough, harrow, ridge",
                priority=TaskPriority.HIGH,
                labor_days=area_ha * 3,
                inputs_required=["fuel", "tractor_hours"] if area_ha > 2 else ["hoes", "labor"],
                agent_assignment="CropOperationsAgent",
            ))
        
        # Planting
        plant_months = cal_data.get("planting", [11])
        for i, month in enumerate(plant_months):
            tasks.append(FarmTask(
                task_id=self._next_task_id("PL"),
                task_type=TaskType.PLANTING,
                enterprise=crop,
                month=month,
                week=1 if i == 0 else 3,
                description=f"Plant {crop} on {area_ha:.1f} ha",
                priority=TaskPriority.CRITICAL,
                labor_days=area_ha * 2,
                inputs_required=[f"{crop}_seed", "planter"],
                dependencies=[t.task_id for t in tasks if t.task_type == TaskType.LAND_PREP],
                agent_assignment="PlantAgent",
            ))
        
        # Fertilizing
        for month in cal_data.get("fertilizing", []):
            fert_type = "basal" if month in [10, 11, 12] else "topdress"
            tasks.append(FarmTask(
                task_id=self._next_task_id("FT"),
                task_type=TaskType.FERTILIZING,
                enterprise=crop,
                month=month,
                week=2,
                description=f"Apply {fert_type} fertilizer to {crop}",
                priority=TaskPriority.HIGH,
                labor_days=area_ha * 1,
                inputs_required=["compound_d" if fert_type == "basal" else "ammonium_nitrate"],
                agent_assignment="CropOperationsAgent",
            ))
        
        # Weeding
        for i, month in enumerate(cal_data.get("weeding", [])):
            tasks.append(FarmTask(
                task_id=self._next_task_id("WD"),
                task_type=TaskType.WEEDING,
                enterprise=crop,
                month=month,
                week=2 if i % 2 == 0 else 4,
                description=f"Weeding round {i+1} for {crop}",
                priority=TaskPriority.HIGH if i < 2 else TaskPriority.MEDIUM,
                labor_days=area_ha * 4,
                inputs_required=["hoes", "herbicide"] if area_ha > 1 else ["hoes"],
                agent_assignment="CropOperationsAgent",
            ))
        
        # Pest control (if applicable)
        for month in cal_data.get("pest_control", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("PC"),
                task_type=TaskType.PEST_CONTROL,
                enterprise=crop,
                month=month,
                week=2,
                description=f"Scout and spray {crop} for pests",
                priority=TaskPriority.HIGH,
                labor_days=area_ha * 0.5,
                inputs_required=["pesticide", "sprayer"],
                agent_assignment="CropOperationsAgent",
            ))
        
        # Irrigation (for irrigated crops)
        for month in cal_data.get("irrigation", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("IR"),
                task_type=TaskType.IRRIGATION,
                enterprise=crop,
                month=month,
                week=None,  # Ongoing
                description=f"Irrigation management for {crop}",
                priority=TaskPriority.CRITICAL,
                labor_days=area_ha * 2,
                inputs_required=["water", "pump_fuel"],
                agent_assignment="IrrigationAgent",
            ))
        
        # Harvest
        harvest_months = cal_data.get("harvest", [4, 5])
        for i, month in enumerate(harvest_months):
            tasks.append(FarmTask(
                task_id=self._next_task_id("HV"),
                task_type=TaskType.HARVEST,
                enterprise=crop,
                month=month,
                week=2 if i == 0 else 4,
                description=f"Harvest {crop} from {area_ha:.1f} ha",
                priority=TaskPriority.CRITICAL,
                labor_days=area_ha * 5,
                inputs_required=["storage_bags", "transport"],
                agent_assignment="CropOperationsAgent",
            ))
        
        # Post-harvest (if applicable)
        for month in cal_data.get("post_harvest", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("PH"),
                task_type=TaskType.POST_HARVEST,
                enterprise=crop,
                month=month,
                week=2,
                description=f"Post-harvest processing for {crop}",
                priority=TaskPriority.HIGH,
                labor_days=area_ha * 3,
                inputs_required=["processing_equipment"],
                agent_assignment="CropOperationsAgent",
            ))
        
        # Determine planting and harvest months for calendar
        plant_month = plant_months[0] if plant_months else 11
        harvest_month = harvest_months[-1] if harvest_months else 5
        
        return CropCalendar(
            crop=crop,
            area_ha=area_ha,
            planting_month=plant_month,
            harvest_month=harvest_month,
            tasks=tasks,
        )
    
    def generate_livestock_calendar(
        self,
        livestock: str,
        count: int,
    ) -> LivestockCalendar:
        """
        Generate livestock management calendar.
        """
        cal_data = LIVESTOCK_CALENDARS_ZW.get(livestock, {})
        tasks = []
        
        # Daily feeding/watering (represented as monthly task)
        for month in range(1, 13):
            tasks.append(FarmTask(
                task_id=self._next_task_id("FD"),
                task_type=TaskType.LIVESTOCK_FEEDING,
                enterprise=livestock,
                month=month,
                week=None,  # Daily
                description=f"Daily feeding and watering of {count} {livestock}",
                priority=TaskPriority.CRITICAL,
                labor_days=count * 0.5,  # Approx per month
                inputs_required=["feed", "water"],
                agent_assignment="LivestockOperationsAgent",
            ))
        
        # Breeding
        for month in cal_data.get("breeding", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("BR"),
                task_type=TaskType.BREEDING,
                enterprise=livestock,
                month=month,
                week=1,
                description=f"Breeding management for {livestock}",
                priority=TaskPriority.HIGH,
                labor_days=count * 0.2,
                agent_assignment="LivestockOperationsAgent",
            ))
        
        # Vaccination
        for month in cal_data.get("vaccination", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("VC"),
                task_type=TaskType.LIVESTOCK_HEALTH,
                enterprise=livestock,
                month=month,
                week=2,
                description=f"Vaccination of {count} {livestock}",
                priority=TaskPriority.HIGH,
                labor_days=count * 0.1,
                inputs_required=["vaccines", "vet_supplies"],
                agent_assignment="SecurityBiosecurityAgent",
            ))
        
        # Deworming
        for month in cal_data.get("deworming", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("DW"),
                task_type=TaskType.LIVESTOCK_HEALTH,
                enterprise=livestock,
                month=month,
                week=3,
                description=f"Deworming of {livestock}",
                priority=TaskPriority.MEDIUM,
                labor_days=count * 0.05,
                inputs_required=["dewormers"],
                agent_assignment="LivestockOperationsAgent",
            ))
        
        # Dipping (cattle)
        for month in cal_data.get("dipping", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("DP"),
                task_type=TaskType.LIVESTOCK_HEALTH,
                enterprise=livestock,
                month=month,
                week=1,  # Weekly activity
                description=f"Tick control dipping for {livestock}",
                priority=TaskPriority.HIGH,
                labor_days=count * 0.3,
                inputs_required=["dip_chemicals"],
                agent_assignment="LivestockOperationsAgent",
            ))
        
        # Marketing
        for month in cal_data.get("marketing", []):
            tasks.append(FarmTask(
                task_id=self._next_task_id("MK"),
                task_type=TaskType.MARKETING,
                enterprise=livestock,
                month=month,
                week=4,
                description=f"Market assessment and sales for {livestock}",
                priority=TaskPriority.MEDIUM,
                labor_days=2,
                agent_assignment="FarmManagementOrchestrator",
            ))
        
        return LivestockCalendar(
            livestock=livestock,
            count=count,
            tasks=tasks,
        )
    
    def generate_schedule(
        self,
        crop_allocations: Dict[str, float],
        livestock_counts: Dict[str, int],
        zone: str = "II",
    ) -> FarmSchedule:
        """
        Generate complete farm schedule from allocations.
        
        Args:
            crop_allocations: Dict of crop -> hectares
            livestock_counts: Dict of livestock -> count
            zone: AEZ zone for timing adjustments
            
        Returns:
            Complete FarmSchedule for the year
        """
        self._task_counter = 0  # Reset counter
        
        # Generate crop calendars
        crop_calendars = []
        for crop, area in crop_allocations.items():
            if area > 0:
                cal = self.generate_crop_calendar(crop, area, zone)
                crop_calendars.append(cal)
        
        # Generate livestock calendars
        livestock_calendars = []
        for livestock, count in livestock_counts.items():
            if count > 0:
                cal = self.generate_livestock_calendar(livestock, count)
                livestock_calendars.append(cal)
        
        # Calculate monthly summaries
        monthly_summary = {}
        for month in range(1, 13):
            month_tasks = []
            for cal in crop_calendars:
                month_tasks.extend([t for t in cal.tasks if t.month == month])
            for cal in livestock_calendars:
                month_tasks.extend([t for t in cal.tasks if t.month == month])
            
            labor = sum(t.labor_days for t in month_tasks)
            critical = len([t for t in month_tasks if t.priority == TaskPriority.CRITICAL])
            
            monthly_summary[month] = {
                "task_count": len(month_tasks),
                "labor_days": round(labor, 1),
                "critical_tasks": critical,
                "enterprises_active": list(set(t.enterprise for t in month_tasks)),
            }
        
        # Find totals and peak
        total_labor = sum(m["labor_days"] for m in monthly_summary.values())
        peak_month = max(monthly_summary.keys(), key=lambda m: monthly_summary[m]["labor_days"])
        peak_labor = monthly_summary[peak_month]["labor_days"]
        
        return FarmSchedule(
            year=self.year,
            crop_calendars=crop_calendars,
            livestock_calendars=livestock_calendars,
            monthly_summary=monthly_summary,
            total_labor_days=round(total_labor, 1),
            peak_month=peak_month,
            peak_labor_days=round(peak_labor, 1),
        )


if __name__ == "__main__":
    agent = SchedulerAgent(year=2026)
    
    crops = {"maize": 2.5, "groundnuts": 1.0, "vegetables": 0.5, "fodder": 1.0}
    livestock = {"goats": 12, "poultry": 100}
    
    schedule = agent.generate_schedule(crops, livestock)
    
    print(f"Farm Schedule {schedule.year}")
    print(f"Total labor: {schedule.total_labor_days} days")
    print(f"Peak month: {schedule.peak_month} ({schedule.peak_labor_days} days)")
    
    print("\nMonthly breakdown:")
    for month, summary in schedule.monthly_summary.items():
        print(f"  Month {month}: {summary['labor_days']:.0f} days, {summary['task_count']} tasks")
