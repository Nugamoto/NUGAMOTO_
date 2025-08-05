"""CRUD helper functions for device types, appliances, and kitchen tools."""

from __future__ import annotations

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session, selectinload

from backend.models.device import DeviceType, Appliance, KitchenTool
from backend.models.kitchen import Kitchen
from backend.schemas.device import (
    DeviceTypeCreate, DeviceTypeRead, DeviceTypeUpdate,
    ApplianceCreate, ApplianceRead, ApplianceUpdate, ApplianceWithDeviceType,
    KitchenToolCreate, KitchenToolRead, KitchenToolUpdate, KitchenToolWithDeviceType,
    ApplianceSearchParams, KitchenToolSearchParams, KitchenDeviceSummary
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_device_type_read(device_type_orm: DeviceType) -> DeviceTypeRead:
    """Convert DeviceType ORM to Read schema."""
    return DeviceTypeRead.model_validate(device_type_orm, from_attributes=True)


def build_appliance_read(appliance_orm: Appliance) -> ApplianceRead:
    """Convert Appliance ORM to Read schema."""
    return ApplianceRead.model_validate(appliance_orm, from_attributes=True)


def build_appliance_with_device_type(appliance_orm: Appliance) -> ApplianceWithDeviceType:
    """Convert Appliance ORM with device type to extended schema."""
    # Build base appliance schema
    base_data = ApplianceRead.model_validate(appliance_orm, from_attributes=True)

    # Add device type information
    device_type_name = appliance_orm.device_type.name if appliance_orm.device_type else "Unknown"
    device_type_category = appliance_orm.device_type.category if appliance_orm.device_type else "unknown"

    # Create extended schema
    return ApplianceWithDeviceType(
        **base_data.model_dump(),
        device_type_name=device_type_name,
        device_type_category=device_type_category
    )


def build_kitchen_tool_read(tool_orm: KitchenTool) -> KitchenToolRead:
    """Convert KitchenTool ORM to Read schema."""
    return KitchenToolRead.model_validate(tool_orm, from_attributes=True)


def build_kitchen_tool_with_device_type(tool_orm: KitchenTool) -> KitchenToolWithDeviceType:
    """Convert KitchenTool ORM with device type to extended schema."""
    # Build base tool schema
    base_data = KitchenToolRead.model_validate(tool_orm, from_attributes=True)

    # Add device type information
    device_type_name = tool_orm.device_type.name if tool_orm.device_type else "Unknown"
    device_type_category = tool_orm.device_type.category if tool_orm.device_type else "unknown"

    # Create extended schema
    return KitchenToolWithDeviceType(
        **base_data.model_dump(),
        device_type_name=device_type_name,
        device_type_category=device_type_category
    )


# ================================================================== #
# DeviceType CRUD Operations - Schema Returns                       #
# ================================================================== #

def create_device_type(db: Session, device_type_data: DeviceTypeCreate) -> DeviceTypeRead:
    """Create a new device type - returns schema."""
    # Check for duplicate name
    existing = db.scalar(
        select(DeviceType).where(DeviceType.name == device_type_data.name)
    )
    if existing:
        raise ValueError(f"Device type with name '{device_type_data.name}' already exists")

    device_type_orm = DeviceType(**device_type_data.model_dump())
    db.add(device_type_orm)
    db.commit()
    db.refresh(device_type_orm)

    return build_device_type_read(device_type_orm)


def get_device_type_by_id(db: Session, device_type_id: int) -> DeviceTypeRead | None:
    """Get device type by ID - returns schema."""
    device_type_orm = db.scalar(
        select(DeviceType).where(DeviceType.id == device_type_id)
    )

    if not device_type_orm:
        return None

    return build_device_type_read(device_type_orm)


def get_device_type_by_name(db: Session, name: str) -> DeviceTypeRead | None:
    """Get device type by name - returns schema."""
    device_type_orm = db.scalar(
        select(DeviceType).where(DeviceType.name.ilike(f"%{name}%"))
    )

    if not device_type_orm:
        return None

    return build_device_type_read(device_type_orm)


def get_all_device_types(db: Session) -> list[DeviceTypeRead]:
    """Get all device types - returns schemas."""
    device_types = db.scalars(
        select(DeviceType).order_by(DeviceType.category, DeviceType.name)
    ).all()

    return [build_device_type_read(dt) for dt in device_types]


def get_device_types_by_category(db: Session, category: str) -> list[DeviceTypeRead]:
    """Get device types by category - returns schemas."""
    device_types = db.scalars(
        select(DeviceType)
        .where(DeviceType.category == category)
        .order_by(DeviceType.name)
    ).all()

    return [build_device_type_read(dt) for dt in device_types]


def update_device_type(
        db: Session, device_type_id: int, device_type_data: DeviceTypeUpdate
) -> DeviceTypeRead | None:
    """Update device type - returns schema."""
    device_type_orm = db.scalar(
        select(DeviceType).where(DeviceType.id == device_type_id)
    )

    if not device_type_orm:
        return None

    # Check for name conflicts if name is being updated
    update_data = device_type_data.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = db.scalar(
            select(DeviceType).where(
                and_(
                    DeviceType.name == update_data["name"],
                    DeviceType.id != device_type_id
                )
            )
        )
        if existing:
            raise ValueError(f"Device type with name '{update_data['name']}' already exists")

    # Apply updates
    for field, value in update_data.items():
        setattr(device_type_orm, field, value)

    db.commit()
    db.refresh(device_type_orm)

    return build_device_type_read(device_type_orm)


def delete_device_type(db: Session, device_type_id: int) -> bool:
    """Delete device type - returns success status."""
    device_type_orm = db.scalar(
        select(DeviceType).where(DeviceType.id == device_type_id)
    )

    if not device_type_orm:
        return False

    # Check if device type is in use
    appliance_count = db.scalar(
        select(func.count(Appliance.id)).where(Appliance.device_type_id == device_type_id)
    )
    tool_count = db.scalar(
        select(func.count(KitchenTool.id)).where(KitchenTool.device_type_id == device_type_id)
    )

    if appliance_count > 0 or tool_count > 0:
        raise ValueError("Cannot delete device type that is in use by appliances or tools")

    db.delete(device_type_orm)
    db.commit()

    return True


# ================================================================== #
# Appliance CRUD Operations - Schema Returns                        #
# ================================================================== #

def create_appliance(
        db: Session, kitchen_id: int, appliance_data: ApplianceCreate
) -> ApplianceRead:
    """Create a new appliance - returns schema."""
    # Verify kitchen exists
    kitchen = db.scalar(select(Kitchen).where(Kitchen.id == kitchen_id))
    if not kitchen:
        raise ValueError("Kitchen not found")

    # Verify device type exists
    device_type = db.scalar(
        select(DeviceType).where(DeviceType.id == appliance_data.device_type_id)
    )
    if not device_type:
        raise ValueError("Device type not found")

    appliance_orm = Appliance(
        kitchen_id=kitchen_id,
        **appliance_data.model_dump()
    )
    db.add(appliance_orm)
    db.commit()
    db.refresh(appliance_orm)

    return build_appliance_read(appliance_orm)


def get_appliance_by_id(db: Session, appliance_id: int) -> ApplianceRead | None:
    """Get appliance by ID - returns schema."""
    appliance_orm = db.scalar(
        select(Appliance).where(Appliance.id == appliance_id)
    )

    if not appliance_orm:
        return None

    return build_appliance_read(appliance_orm)


def get_kitchen_appliances(db: Session, kitchen_id: int) -> list[ApplianceWithDeviceType]:
    """Get all appliances for a kitchen with device type info - returns schemas."""
    appliances = db.scalars(
        select(Appliance)
        .options(selectinload(Appliance.device_type))
        .where(Appliance.kitchen_id == kitchen_id)
        .order_by(Appliance.name)
    ).all()

    return [build_appliance_with_device_type(app) for app in appliances]


def search_appliances(
        db: Session, kitchen_id: int, search_params: ApplianceSearchParams
) -> list[ApplianceWithDeviceType]:
    """Search appliances with filters - returns schemas."""
    query = select(Appliance).options(selectinload(Appliance.device_type))
    query = query.where(Appliance.kitchen_id == kitchen_id)

    # Apply search filters
    if search_params.device_type_id is not None:
        query = query.where(Appliance.device_type_id == search_params.device_type_id)

    if search_params.brand is not None:
        query = query.where(Appliance.brand.ilike(f"%{search_params.brand}%"))

    if search_params.smart is not None:
        query = query.where(Appliance.smart == search_params.smart)

    if search_params.available is not None:
        query = query.where(Appliance.available == search_params.available)

    if search_params.min_power_watts is not None:
        query = query.where(Appliance.power_watts >= search_params.min_power_watts)

    if search_params.max_power_watts is not None:
        query = query.where(Appliance.power_watts <= search_params.max_power_watts)

    if search_params.min_power_kw is not None:
        query = query.where(Appliance.power_kw >= search_params.min_power_kw)

    if search_params.max_power_kw is not None:
        query = query.where(Appliance.power_kw <= search_params.max_power_kw)

    if search_params.min_capacity_liters is not None:
        query = query.where(Appliance.capacity_liters >= search_params.min_capacity_liters)

    if search_params.max_capacity_liters is not None:
        query = query.where(Appliance.capacity_liters <= search_params.max_capacity_liters)

    query = query.order_by(Appliance.name)
    appliances = db.scalars(query).all()

    return [build_appliance_with_device_type(app) for app in appliances]


def update_appliance(
        db: Session, appliance_id: int, appliance_data: ApplianceUpdate
) -> ApplianceRead | None:
    """Update appliance - returns schema."""
    appliance_orm = db.scalar(
        select(Appliance).where(Appliance.id == appliance_id)
    )

    if not appliance_orm:
        return None

    # Apply updates
    update_data = appliance_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appliance_orm, field, value)

    db.commit()
    db.refresh(appliance_orm)

    return build_appliance_read(appliance_orm)


def delete_appliance(db: Session, appliance_id: int) -> bool:
    """Delete appliance - returns success status."""
    appliance_orm = db.scalar(
        select(Appliance).where(Appliance.id == appliance_id)
    )

    if not appliance_orm:
        return False

    db.delete(appliance_orm)
    db.commit()

    return True


# ================================================================== #
# KitchenTool CRUD Operations - Schema Returns                      #
# ================================================================== #

def create_kitchen_tool(
        db: Session, kitchen_id: int, tool_data: KitchenToolCreate
) -> KitchenToolRead:
    """Create a new kitchen tool - returns schema."""
    # Verify kitchen exists
    kitchen = db.scalar(select(Kitchen).where(Kitchen.id == kitchen_id))
    if not kitchen:
        raise ValueError("Kitchen not found")

    # Verify device type exists
    device_type = db.scalar(
        select(DeviceType).where(DeviceType.id == tool_data.device_type_id)
    )
    if not device_type:
        raise ValueError("Device type not found")

    tool_orm = KitchenTool(
        kitchen_id=kitchen_id,
        **tool_data.model_dump()
    )
    db.add(tool_orm)
    db.commit()
    db.refresh(tool_orm)

    return build_kitchen_tool_read(tool_orm)


def get_kitchen_tool_by_id(db: Session, tool_id: int) -> KitchenToolRead | None:
    """Get kitchen tool by ID - returns schema."""
    tool_orm = db.scalar(
        select(KitchenTool).where(KitchenTool.id == tool_id)
    )

    if not tool_orm:
        return None

    return build_kitchen_tool_read(tool_orm)


def get_kitchen_tools(db: Session, kitchen_id: int) -> list[KitchenToolWithDeviceType]:
    """Get all kitchen tools for a kitchen with device type info - returns schemas."""
    tools = db.scalars(
        select(KitchenTool)
        .options(selectinload(KitchenTool.device_type))
        .where(KitchenTool.kitchen_id == kitchen_id)
        .order_by(KitchenTool.name)
    ).all()

    return [build_kitchen_tool_with_device_type(tool) for tool in tools]


def search_kitchen_tools(
        db: Session, kitchen_id: int, search_params: KitchenToolSearchParams
) -> list[KitchenToolWithDeviceType]:
    """Search kitchen tools with filters - returns schemas."""
    query = select(KitchenTool).options(selectinload(KitchenTool.device_type))
    query = query.where(KitchenTool.kitchen_id == kitchen_id)

    # Apply search filters
    if search_params.device_type_id is not None:
        query = query.where(KitchenTool.device_type_id == search_params.device_type_id)

    if search_params.material is not None:
        query = query.where(KitchenTool.material.ilike(f"%{search_params.material}%"))

    if search_params.available is not None:
        query = query.where(KitchenTool.available == search_params.available)

    if search_params.min_quantity is not None:
        query = query.where(KitchenTool.quantity >= search_params.min_quantity)

    if search_params.is_set is not None:
        if search_params.is_set:
            query = query.where(KitchenTool.quantity > 1)
        else:
            query = query.where(KitchenTool.quantity == 1)

    query = query.order_by(KitchenTool.name)
    tools = db.scalars(query).all()

    return [build_kitchen_tool_with_device_type(tool) for tool in tools]


def update_kitchen_tool(
        db: Session, tool_id: int, tool_data: KitchenToolUpdate
) -> KitchenToolRead | None:
    """Update kitchen tool - returns schema."""
    tool_orm = db.scalar(
        select(KitchenTool).where(KitchenTool.id == tool_id)
    )

    if not tool_orm:
        return None

    # Apply updates
    update_data = tool_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool_orm, field, value)

    db.commit()
    db.refresh(tool_orm)

    return build_kitchen_tool_read(tool_orm)


def delete_kitchen_tool(db: Session, tool_id: int) -> bool:
    """Delete kitchen tool - returns success status."""
    tool_orm = db.scalar(
        select(KitchenTool).where(KitchenTool.id == tool_id)
    )

    if not tool_orm:
        return False

    db.delete(tool_orm)
    db.commit()

    return True


# ================================================================== #
# Summary and Analytics                                              #
# ================================================================== #

def get_kitchen_device_summary(db: Session, kitchen_id: int) -> KitchenDeviceSummary:
    """Get device summary for a kitchen - returns schema."""
    # Count appliances using func.count() for better performance
    total_appliances = db.scalar(
        select(func.count(Appliance.id)).where(Appliance.kitchen_id == kitchen_id)
    ) or 0

    available_appliances = db.scalar(
        select(func.count(Appliance.id)).where(
            and_(Appliance.kitchen_id == kitchen_id, Appliance.available == True)
        )
    ) or 0

    smart_appliances = db.scalar(
        select(func.count(Appliance.id)).where(
            and_(Appliance.kitchen_id == kitchen_id, Appliance.smart == True)
        )
    ) or 0

    # Count tools
    total_tools = db.scalar(
        select(func.count(KitchenTool.id)).where(KitchenTool.kitchen_id == kitchen_id)
    ) or 0

    available_tools = db.scalar(
        select(func.count(KitchenTool.id)).where(
            and_(KitchenTool.kitchen_id == kitchen_id, KitchenTool.available == True)
        )
    ) or 0

    # Get unique device types used - properly convert to lists
    appliance_device_types = list(db.scalars(
        select(Appliance.device_type_id).where(Appliance.kitchen_id == kitchen_id)
    ).all())

    tool_device_types = list(db.scalars(
        select(KitchenTool.device_type_id).where(KitchenTool.kitchen_id == kitchen_id)
    ).all())

    device_types_used = len(set(appliance_device_types + tool_device_types))

    return KitchenDeviceSummary(
        kitchen_id=kitchen_id,
        total_appliances=total_appliances,
        total_tools=total_tools,
        available_appliances=available_appliances,
        available_tools=available_tools,
        smart_appliances=smart_appliances,
        device_types_used=device_types_used
    )


# ================================================================== #
# ORM-based Functions (for internal use when ORM objects needed)     #
# ================================================================== #

def get_device_type_orm_by_id(db: Session, device_type_id: int) -> DeviceType | None:
    """Get DeviceType ORM object by ID - for internal use."""
    return db.scalar(
        select(DeviceType).where(DeviceType.id == device_type_id)
    )


def get_appliance_orm_by_id(db: Session, appliance_id: int) -> Appliance | None:
    """Get Appliance ORM object by ID - for internal use."""
    return db.scalar(
        select(Appliance).where(Appliance.id == appliance_id)
    )


def get_kitchen_tool_orm_by_id(db: Session, tool_id: int) -> KitchenTool | None:
    """Get KitchenTool ORM object by ID - for internal use."""
    return db.scalar(
        select(KitchenTool).where(KitchenTool.id == tool_id)
    )