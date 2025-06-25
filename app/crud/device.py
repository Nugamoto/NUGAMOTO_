"""CRUD operations for kitchen devices and tools."""

from __future__ import annotations

import datetime

from sqlalchemy import and_, func, select, Integer
from sqlalchemy.orm import Session, selectinload

from app.models.device import Appliance, DeviceType, KitchenTool
from app.schemas.device import (
    ApplianceCreate,
    ApplianceSearchParams,
    ApplianceUpdate,
    ApplianceWithDeviceType,
    DeviceTypeCreate,
    DeviceTypeUpdate,
    KitchenDeviceSummary,
    KitchenToolCreate,
    KitchenToolSearchParams,
    KitchenToolUpdate,
    KitchenToolWithDeviceType,
)


# ================================================================== #
# DeviceType CRUD Operations                                         #
# ================================================================== #

def create_device_type(db: Session, device_type_data: DeviceTypeCreate) -> DeviceType:
    """Create a new device type.
    
    Args:
        db: Database session.
        device_type_data: Device type creation data.
        
    Returns:
        The created device type.
        
    Raises:
        ValueError: If device type with this name already exists.
    """
    # Check if device type with this name already exists
    existing = get_device_type_by_name(db, device_type_data.name)
    if existing:
        raise ValueError(f"Device type with name '{device_type_data.name}' already exists")

    db_device_type = DeviceType(
        name=device_type_data.name,
        category=device_type_data.category,
        default_smart=device_type_data.default_smart,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )

    db.add(db_device_type)
    db.commit()
    db.refresh(db_device_type)

    return db_device_type


def get_device_type_by_id(db: Session, device_type_id: int) -> DeviceType | None:
    """Get device type by ID.
    
    Args:
        db: Database session.
        device_type_id: ID of the device type.
        
    Returns:
        The device type or None if not found.
        
    Raises:
        ValueError: If device_type_id is invalid.
    """
    if device_type_id <= 0:
        raise ValueError("Device type ID must be positive")

    stmt = select(DeviceType).where(DeviceType.id == device_type_id)
    return db.scalar(stmt)


def get_device_type_by_name(db: Session, name: str) -> DeviceType | None:
    """Get device type by name.
    
    Args:
        db: Database session.
        name: Name of the device type.
        
    Returns:
        The device type or None if not found.
    """
    stmt = select(DeviceType).where(DeviceType.name == name)
    return db.scalar(stmt)


def get_all_device_types(db: Session, skip: int = 0, limit: int = 100) -> list[DeviceType]:
    """Get all device types with pagination.
    
    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        
    Returns:
        List of device types.
        
    Raises:
        ValueError: If pagination parameters are invalid.
    """
    if skip < 0:
        raise ValueError("Skip must be non-negative")
    if limit <= 0:
        raise ValueError("Limit must be positive")

    stmt = select(DeviceType).offset(skip).limit(limit).order_by(DeviceType.name)
    return list(db.scalars(stmt).all())


def get_device_types_by_category(db: Session, category: str) -> list[DeviceType]:
    """Get device types by category.
    
    Args:
        db: Database session.
        category: Category to filter by.
        
    Returns:
        List of device types in the specified category.
    """
    stmt = select(DeviceType).where(DeviceType.category == category).order_by(DeviceType.name)
    return list(db.scalars(stmt).all())


def update_device_type(
        db: Session,
        device_type_id: int,
        device_type_data: DeviceTypeUpdate
) -> DeviceType:
    """Update an existing device type.
    
    Args:
        db: Database session.
        device_type_id: ID of the device type to update.
        device_type_data: Updated device type data.
        
    Returns:
        The updated device type.
        
    Raises:
        ValueError: If device type not found or name conflict exists.
    """
    device_type = get_device_type_by_id(db, device_type_id)
    if not device_type:
        raise ValueError(f"Device type with ID {device_type_id} not found")

    # Check for name conflicts if name is being changed
    if device_type_data.name and device_type_data.name != device_type.name:
        existing = get_device_type_by_name(db, device_type_data.name)
        if existing:
            raise ValueError(f"Device type with name '{device_type_data.name}' already exists")

    # Update fields
    update_data = device_type_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device_type, field, value)

    db.commit()
    db.refresh(device_type)

    return device_type


def delete_device_type(db: Session, device_type_id: int) -> bool:
    """Delete a device type.
    
    Args:
        db: Database session.
        device_type_id: ID of the device type to delete.
        
    Returns:
        True if deleted successfully.
        
    Raises:
        ValueError: If device type not found or still has associated devices.
    """
    device_type = get_device_type_by_id(db, device_type_id)
    if not device_type:
        raise ValueError(f"Device type with ID {device_type_id} not found")

    # Check if device type is still in use
    if device_type.total_instances > 0:
        raise ValueError(
            f"Cannot delete device type '{device_type.name}' - it has {device_type.total_instances} associated devices")

    db.delete(device_type)
    db.commit()

    return True


# ================================================================== #
# Appliance CRUD Operations                                          #
# ================================================================== #

def create_appliance(
        db: Session,
        kitchen_id: int,
        appliance_data: ApplianceCreate
) -> ApplianceWithDeviceType:
    """Create a new appliance for a kitchen.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        appliance_data: Appliance creation data.
        
    Returns:
        The created appliance with device type information.
        
    Raises:
        ValueError: If kitchen_id or device_type_id is invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    # Verify device type exists
    device_type = get_device_type_by_id(db, appliance_data.device_type_id)
    if not device_type:
        raise ValueError(f"Device type with ID {appliance_data.device_type_id} not found")

    db_appliance = Appliance(
        kitchen_id=kitchen_id,
        device_type_id=appliance_data.device_type_id,
        name=appliance_data.name,
        brand=appliance_data.brand,
        model=appliance_data.model,
        smart=appliance_data.smart,
        capacity_liters=appliance_data.capacity_liters,
        power_watts=appliance_data.power_watts,
        power_kw=appliance_data.power_kw,
        year_purchased=appliance_data.year_purchased,
        available=appliance_data.available,
        notes=appliance_data.notes,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )

    db.add(db_appliance)
    db.commit()
    db.refresh(db_appliance)

    # Load device type relationship for response
    db.refresh(db_appliance, ["device_type"])

    return _build_appliance_with_device_type(db_appliance)


def get_appliance_by_id(
        db: Session,
        appliance_id: int,
        kitchen_id: int | None = None
) -> ApplianceWithDeviceType | None:
    """Get appliance by ID with optional kitchen validation.
    
    Args:
        db: Database session.
        appliance_id: ID of the appliance.
        kitchen_id: Optional kitchen ID for ownership validation.
        
    Returns:
        The appliance with device type information or None if not found.
        
    Raises:
        ValueError: If IDs are invalid or appliance doesn't belong to kitchen.
    """
    if appliance_id <= 0:
        raise ValueError("Appliance ID must be positive")

    if kitchen_id is not None and kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    stmt = (
        select(Appliance)
        .options(selectinload(Appliance.device_type))
        .where(Appliance.id == appliance_id)
    )

    appliance = db.scalar(stmt)
    if not appliance:
        return None

    # Validate kitchen ownership if specified
    if kitchen_id is not None and appliance.kitchen_id != kitchen_id:
        raise ValueError(f"Appliance {appliance_id} does not belong to kitchen {kitchen_id}")

    return _build_appliance_with_device_type(appliance)


def get_kitchen_appliances(
        db: Session,
        kitchen_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[ApplianceWithDeviceType]:
    """Get all appliances for a kitchen with pagination.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        
    Returns:
        List of appliances with device type information.
        
    Raises:
        ValueError: If parameters are invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")
    if skip < 0:
        raise ValueError("Skip must be non-negative")
    if limit <= 0:
        raise ValueError("Limit must be positive")

    stmt = (
        select(Appliance)
        .options(selectinload(Appliance.device_type))
        .where(Appliance.kitchen_id == kitchen_id)
        .offset(skip)
        .limit(limit)
        .order_by(Appliance.name)
    )

    appliances = db.scalars(stmt).all()
    return [_build_appliance_with_device_type(appliance) for appliance in appliances]


def search_appliances(
        db: Session,
        kitchen_id: int,
        search_params: ApplianceSearchParams
) -> list[ApplianceWithDeviceType]:
    """Search appliances by various criteria.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        search_params: Search filter parameters.
        
    Returns:
        List of matching appliances with device type information.
        
    Raises:
        ValueError: If kitchen_id is invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    stmt = (
        select(Appliance)
        .options(selectinload(Appliance.device_type))
        .where(Appliance.kitchen_id == kitchen_id)
    )

    # Apply filters
    if search_params.device_type_id is not None:
        stmt = stmt.where(Appliance.device_type_id == search_params.device_type_id)
    if search_params.brand is not None:
        stmt = stmt.where(Appliance.brand.ilike(f"%{search_params.brand}%"))
    if search_params.smart is not None:
        stmt = stmt.where(Appliance.smart == search_params.smart)
    if search_params.available is not None:
        stmt = stmt.where(Appliance.available == search_params.available)
    if search_params.min_power_watts is not None:
        stmt = stmt.where(Appliance.power_watts >= search_params.min_power_watts)
    if search_params.max_power_watts is not None:
        stmt = stmt.where(Appliance.power_watts <= search_params.max_power_watts)
    if search_params.min_power_kw is not None:
        stmt = stmt.where(Appliance.power_kw >= search_params.min_power_kw)
    if search_params.max_power_kw is not None:
        stmt = stmt.where(Appliance.power_kw <= search_params.max_power_kw)
    if search_params.min_capacity_liters is not None:
        stmt = stmt.where(Appliance.capacity_liters >= search_params.min_capacity_liters)
    if search_params.max_capacity_liters is not None:
        stmt = stmt.where(Appliance.capacity_liters <= search_params.max_capacity_liters)

    appliances = db.scalars(stmt.order_by(Appliance.name)).all()
    return [_build_appliance_with_device_type(appliance) for appliance in appliances]


def update_appliance(
        db: Session,
        appliance_id: int,
        kitchen_id: int,
        appliance_data: ApplianceUpdate
) -> ApplianceWithDeviceType:
    """Update an existing appliance.
    
    Args:
        db: Database session.
        appliance_id: ID of the appliance to update.
        kitchen_id: ID of the kitchen for ownership validation.
        appliance_data: Updated appliance data.
        
    Returns:
        The updated appliance with device type information.
        
    Raises:
        ValueError: If appliance not found or doesn't belong to kitchen.
    """
    appliance = get_appliance_by_id(db, appliance_id, kitchen_id)
    if not appliance:
        raise ValueError(f"Appliance with ID {appliance_id} not found in kitchen {kitchen_id}")

    # Get the actual model instance for updating
    stmt = select(Appliance).where(Appliance.id == appliance_id)
    db_appliance = db.scalar(stmt)

    # Update fields
    update_data = appliance_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_appliance, field, value)

    db_appliance.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(db_appliance, ["device_type"])

    return _build_appliance_with_device_type(db_appliance)


def delete_appliance(db: Session, appliance_id: int, kitchen_id: int) -> bool:
    """Delete an appliance.
    
    Args:
        db: Database session.
        appliance_id: ID of the appliance to delete.
        kitchen_id: ID of the kitchen for ownership validation.
        
    Returns:
        True if deleted successfully.
        
    Raises:
        ValueError: If appliance not found or doesn't belong to kitchen.
    """
    appliance = get_appliance_by_id(db, appliance_id, kitchen_id)
    if not appliance:
        raise ValueError(f"Appliance with ID {appliance_id} not found in kitchen {kitchen_id}")

    # Get the actual model instance for deletion
    stmt = select(Appliance).where(Appliance.id == appliance_id)
    db_appliance = db.scalar(stmt)

    db.delete(db_appliance)
    db.commit()

    return True


# ================================================================== #
# KitchenTool CRUD Operations                                        #
# ================================================================== #

def create_kitchen_tool(
        db: Session,
        kitchen_id: int,
        tool_data: KitchenToolCreate
) -> KitchenToolWithDeviceType:
    """Create a new kitchen tool.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        tool_data: Tool creation data.
        
    Returns:
        The created tool with device type information.
        
    Raises:
        ValueError: If kitchen_id or device_type_id is invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    # Verify device type exists
    device_type = get_device_type_by_id(db, tool_data.device_type_id)
    if not device_type:
        raise ValueError(f"Device type with ID {tool_data.device_type_id} not found")

    db_tool = KitchenTool(
        kitchen_id=kitchen_id,
        device_type_id=tool_data.device_type_id,
        name=tool_data.name,
        size_or_detail=tool_data.size_or_detail,
        material=tool_data.material,
        quantity=tool_data.quantity,
        available=tool_data.available,
        notes=tool_data.notes,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )

    db.add(db_tool)
    db.commit()
    db.refresh(db_tool, ["device_type"])

    return _build_kitchen_tool_with_device_type(db_tool)


def get_kitchen_tool_by_id(
        db: Session,
        tool_id: int,
        kitchen_id: int | None = None
) -> KitchenToolWithDeviceType | None:
    """Get kitchen tool by ID with optional kitchen validation.
    
    Args:
        db: Database session.
        tool_id: ID of the tool.
        kitchen_id: Optional kitchen ID for ownership validation.
        
    Returns:
        The tool with device type information or None if not found.
        
    Raises:
        ValueError: If IDs are invalid or tool doesn't belong to kitchen.
    """
    if tool_id <= 0:
        raise ValueError("Tool ID must be positive")

    if kitchen_id is not None and kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    stmt = (
        select(KitchenTool)
        .options(selectinload(KitchenTool.device_type))
        .where(KitchenTool.id == tool_id)
    )

    tool = db.scalar(stmt)
    if not tool:
        return None

    # Validate kitchen ownership if specified
    if kitchen_id is not None and tool.kitchen_id != kitchen_id:
        raise ValueError(f"Tool {tool_id} does not belong to kitchen {kitchen_id}")

    return _build_kitchen_tool_with_device_type(tool)


def get_kitchen_tools(
        db: Session,
        kitchen_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[KitchenToolWithDeviceType]:
    """Get all kitchen tools for a kitchen with pagination.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        
    Returns:
        List of tools with device type information.
        
    Raises:
        ValueError: If parameters are invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")
    if skip < 0:
        raise ValueError("Skip must be non-negative")
    if limit <= 0:
        raise ValueError("Limit must be positive")

    stmt = (
        select(KitchenTool)
        .options(selectinload(KitchenTool.device_type))
        .where(KitchenTool.kitchen_id == kitchen_id)
        .offset(skip)
        .limit(limit)
        .order_by(KitchenTool.name)
    )

    tools = db.scalars(stmt).all()
    return [_build_kitchen_tool_with_device_type(tool) for tool in tools]


def search_kitchen_tools(
        db: Session,
        kitchen_id: int,
        search_params: KitchenToolSearchParams
) -> list[KitchenToolWithDeviceType]:
    """Search kitchen tools by various criteria.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        search_params: Search filter parameters.
        
    Returns:
        List of matching tools with device type information.
        
    Raises:
        ValueError: If kitchen_id is invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    stmt = (
        select(KitchenTool)
        .options(selectinload(KitchenTool.device_type))
        .where(KitchenTool.kitchen_id == kitchen_id)
    )

    # Apply filters
    if search_params.device_type_id is not None:
        stmt = stmt.where(KitchenTool.device_type_id == search_params.device_type_id)
    if search_params.material is not None:
        stmt = stmt.where(KitchenTool.material.ilike(f"%{search_params.material}%"))
    if search_params.available is not None:
        stmt = stmt.where(KitchenTool.available == search_params.available)
    if search_params.min_quantity is not None:
        stmt = stmt.where(KitchenTool.quantity >= search_params.min_quantity)
    if search_params.is_set is not None:
        if search_params.is_set:
            stmt = stmt.where(and_(KitchenTool.quantity.is_not(None), KitchenTool.quantity > 1))
        else:
            stmt = stmt.where(KitchenTool.quantity.is_(None) | (KitchenTool.quantity <= 1))

    tools = db.scalars(stmt.order_by(KitchenTool.name)).all()
    return [_build_kitchen_tool_with_device_type(tool) for tool in tools]


def update_kitchen_tool(
        db: Session,
        tool_id: int,
        kitchen_id: int,
        tool_data: KitchenToolUpdate
) -> KitchenToolWithDeviceType:
    """Update an existing kitchen tool.
    
    Args:
        db: Database session.
        tool_id: ID of the tool to update.
        kitchen_id: ID of the kitchen for ownership validation.
        tool_data: Updated tool data.
        
    Returns:
        The updated tool with device type information.
        
    Raises:
        ValueError: If tool not found or doesn't belong to kitchen.
    """
    tool = get_kitchen_tool_by_id(db, tool_id, kitchen_id)
    if not tool:
        raise ValueError(f"Kitchen tool with ID {tool_id} not found in kitchen {kitchen_id}")

    # Get the actual model instance for updating
    stmt = select(KitchenTool).where(KitchenTool.id == tool_id)
    db_tool = db.scalar(stmt)

    # Update fields
    update_data = tool_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tool, field, value)

    db_tool.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(db_tool, ["device_type"])

    return _build_kitchen_tool_with_device_type(db_tool)


def delete_kitchen_tool(db: Session, tool_id: int, kitchen_id: int) -> bool:
    """Delete a kitchen tool.
    
    Args:
        db: Database session.
        tool_id: ID of the tool to delete.
        kitchen_id: ID of the kitchen for ownership validation.
        
    Returns:
        True if deleted successfully.
        
    Raises:
        ValueError: If tool not found or doesn't belong to kitchen.
    """
    tool = get_kitchen_tool_by_id(db, tool_id, kitchen_id)
    if not tool:
        raise ValueError(f"Kitchen tool with ID {tool_id} not found in kitchen {kitchen_id}")

    # Get the actual model instance for deletion
    stmt = select(KitchenTool).where(KitchenTool.id == tool_id)
    db_tool = db.scalar(stmt)

    db.delete(db_tool)
    db.commit()

    return True


def get_kitchen_device_summary(db: Session, kitchen_id: int) -> KitchenDeviceSummary:
    """Get summary statistics for all devices in a kitchen.
    
    Args:
        db: Database session.
        kitchen_id: ID of the kitchen.
        
    Returns:
        Summary statistics for the kitchen's devices.
        
    Raises:
        ValueError: If kitchen_id is invalid.
    """
    if kitchen_id <= 0:
        raise ValueError("Kitchen ID must be positive")

    # Count appliances
    appliances_stmt = select(
        func.count(Appliance.id).label("total"),
        func.sum(func.cast(Appliance.available, Integer)).label("available"),
        func.sum(func.cast(Appliance.smart, Integer)).label("smart")
    ).where(Appliance.kitchen_id == kitchen_id)
    
    appliance_stats = db.execute(appliances_stmt).first()

    # Count tools
    tools_stmt = select(
        func.count(KitchenTool.id).label("total"),
        func.sum(func.cast(KitchenTool.available, Integer)).label("available")
    ).where(KitchenTool.kitchen_id == kitchen_id)
    
    tool_stats = db.execute(tools_stmt).first()

    # Count unique device types used in appliances
    appliance_types_stmt = select(
        func.count(func.distinct(Appliance.device_type_id)).label("appliance_types")
    ).where(Appliance.kitchen_id == kitchen_id)
    
    db.execute(appliance_types_stmt).scalar() or 0

    # Count unique device types used in tools
    tool_types_stmt = select(
        func.count(func.distinct(KitchenTool.device_type_id)).label("tool_types")
    ).where(KitchenTool.kitchen_id == kitchen_id)
    
    db.execute(tool_types_stmt).scalar() or 0

    # Count total unique device types (union of both)
    unique_types_stmt = select(
        func.count(func.distinct(func.coalesce(Appliance.device_type_id, KitchenTool.device_type_id)))
    ).select_from(
        Appliance.__table__.outerjoin(
            KitchenTool.__table__, 
            and_(
                Appliance.kitchen_id == KitchenTool.kitchen_id,
                Appliance.device_type_id == KitchenTool.device_type_id
            )
        )
    ).where(
        (Appliance.kitchen_id == kitchen_id) | (KitchenTool.kitchen_id == kitchen_id)
    )
    
    total_unique_types = db.execute(unique_types_stmt).scalar() or 0

    return KitchenDeviceSummary(
        kitchen_id=kitchen_id,
        total_appliances=appliance_stats.total or 0,
        total_tools=tool_stats.total or 0,
        available_appliances=appliance_stats.available or 0,
        available_tools=tool_stats.available or 0,
        smart_appliances=appliance_stats.smart or 0,
        device_types_used=total_unique_types
    )


# ================================================================== #
# Helper Functions                                                   #
# ================================================================== #

def _build_appliance_with_device_type(appliance: Appliance) -> ApplianceWithDeviceType:
    """Build ApplianceWithDeviceType from Appliance model instance.
    
    Args:
        appliance: Appliance model instance with device_type loaded.
        
    Returns:
        ApplianceWithDeviceType schema instance.
    """
    return ApplianceWithDeviceType(
        id=appliance.id,
        kitchen_id=appliance.kitchen_id,
        device_type_id=appliance.device_type_id,
        name=appliance.name,
        brand=appliance.brand,
        model=appliance.model,
        smart=appliance.smart,
        capacity_liters=appliance.capacity_liters,
        power_watts=appliance.power_watts,
        power_kw=appliance.power_kw,
        year_purchased=appliance.year_purchased,
        available=appliance.available,
        notes=appliance.notes,
        display_name=appliance.display_name,
        age_years=appliance.age_years,
        created_at=appliance.created_at,
        updated_at=appliance.updated_at,
        device_type_name=appliance.device_type.name,
        device_type_category=appliance.device_type.category
    )


def _build_kitchen_tool_with_device_type(tool: KitchenTool) -> KitchenToolWithDeviceType:
    """Build KitchenToolWithDeviceType from KitchenTool model instance.
    
    Args:
        tool: KitchenTool model instance with device_type loaded.
        
    Returns:
        KitchenToolWithDeviceType schema instance.
    """
    return KitchenToolWithDeviceType(
        id=tool.id,
        kitchen_id=tool.kitchen_id,
        device_type_id=tool.device_type_id,
        name=tool.name,
        size_or_detail=tool.size_or_detail,
        material=tool.material,
        quantity=tool.quantity,
        available=tool.available,
        notes=tool.notes,
        full_description=tool.full_description,
        is_set=tool.is_set,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
        device_type_name=tool.device_type.name,
        device_type_category=tool.device_type.category
    )