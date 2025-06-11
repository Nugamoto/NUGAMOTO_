"""API routes for kitchen devices and tools."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud
from app.core.dependencies import get_db
from app.schemas.device import (
    ApplianceCreate,
    ApplianceSearchParams,
    ApplianceUpdate,
    ApplianceWithDeviceType,
    DeviceTypeCreate,
    DeviceTypeRead,
    DeviceTypeUpdate,
    KitchenDeviceSummary,
    KitchenToolCreate,
    KitchenToolSearchParams,
    KitchenToolUpdate,
    KitchenToolWithDeviceType,
)

# Initialize CRUD operations
crud_device = crud.device

# Create routers
device_types_router = APIRouter(prefix="/device-types", tags=["Device Types"])
appliances_router = APIRouter(prefix="/kitchens", tags=["Appliances"])
tools_router = APIRouter(prefix="/kitchens", tags=["Kitchen Tools"])
summary_router = APIRouter(prefix="/kitchens", tags=["Kitchen Summary"])


# ================================================================== #
# Device Type Routes                                                 #
# ================================================================== #

@device_types_router.post(
    "/",
    response_model=DeviceTypeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create device type"
)
def create_device_type(
        device_type_data: DeviceTypeCreate,
        db: Annotated[Session, Depends(get_db)]
) -> DeviceTypeRead:
    """Create a new device type.

    Args:
        device_type_data: Device type data to create.
        db: Database session dependency.

    Returns:
        The created device type.

    Raises:
        HTTPException: 400 if device type with this name already exists.

    Example:
        ```json
        {
            "name": "Stand Mixer",
            "category": "appliance",
            "default_smart": false
        }
        ```
    """
    try:
        device_type = crud_device.create_device_type(db, device_type_data)
        return DeviceTypeRead.model_validate(device_type, from_attributes=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@device_types_router.get(
    "/",
    response_model=list[DeviceTypeRead],
    summary="Get all device types"
)
def get_all_device_types(
        db: Annotated[Session, Depends(get_db)],
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> list[DeviceTypeRead]:
    """Get all device types with pagination.

    Args:
        db: Database session dependency.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        List of device types.

    Example:
        GET /device-types?skip=0&limit=50
    """
    try:
        device_types = crud_device.get_all_device_types(db, skip=skip, limit=limit)
        return [DeviceTypeRead.model_validate(dt, from_attributes=True) for dt in device_types]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@device_types_router.get(
    "/{device_type_id}",
    response_model=DeviceTypeRead,
    summary="Get device type by ID"
)
def get_device_type(
        device_type_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> DeviceTypeRead:
    """Get a specific device type by ID.

    Args:
        device_type_id: The unique identifier of the device type.
        db: Database session dependency.

    Returns:
        The device type details.

    Raises:
        HTTPException: 404 if device type not found.

    Example:
        GET /device-types/123
    """
    try:
        device_type = crud_device.get_device_type_by_id(db, device_type_id)
        if not device_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device type with ID {device_type_id} not found"
            )
        return DeviceTypeRead.model_validate(device_type, from_attributes=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@device_types_router.put(
    "/{device_type_id}",
    response_model=DeviceTypeRead,
    summary="Update device type"
)
def update_device_type(
        device_type_id: int,
        device_type_data: DeviceTypeUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> DeviceTypeRead:
    """Update an existing device type.

    Args:
        device_type_id: The unique identifier of the device type.
        device_type_data: Updated device type data.
        db: Database session dependency.

    Returns:
        The updated device type.

    Raises:
        HTTPException: 404 if device type not found, 400 if validation fails.

    Example:
        ```json
        {
            "name": "Updated Stand Mixer",
            "default_smart": true
        }
        ```
    """
    try:
        device_type = crud_device.update_device_type(db, device_type_id, device_type_data)
        return DeviceTypeRead.model_validate(device_type, from_attributes=True)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@device_types_router.delete(
    "/{device_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete device type"
)
def delete_device_type(
        device_type_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a device type.

    Args:
        device_type_id: The unique identifier of the device type.
        db: Database session dependency.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if device type not found, 400 if still in use.

    Example:
        DELETE /device-types/123
    """
    try:
        crud_device.delete_device_type(db, device_type_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ================================================================== #
# Appliance Routes                                                   #
# ================================================================== #

@appliances_router.post(
    "/{kitchen_id}/appliances",
    response_model=ApplianceWithDeviceType,
    status_code=status.HTTP_201_CREATED,
    summary="Create appliance"
)
def create_appliance(
        kitchen_id: int,
        appliance_data: ApplianceCreate,
        db: Annotated[Session, Depends(get_db)]
) -> ApplianceWithDeviceType:
    """Create a new appliance in a kitchen.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        appliance_data: Appliance data to create.
        db: Database session dependency.

    Returns:
        The created appliance with device type information.

    Raises:
        HTTPException: 400 if validation fails.

    Example:
        ```json
        {
            "name": "My Oven",
            "device_type_id": 1,
            "brand": "Samsung",
            "model": "NV75K5571RM",
            "power_kw": 3.5,
            "smart": true
        }
        ```
    """
    try:
        return crud_device.create_appliance(db, kitchen_id, appliance_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@appliances_router.get(
    "/{kitchen_id}/appliances",
    response_model=list[ApplianceWithDeviceType],
    summary="Get kitchen appliances"
)
def get_kitchen_appliances(
        kitchen_id: int,
        db: Annotated[Session, Depends(get_db)],
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> list[ApplianceWithDeviceType]:
    """Get all appliances in a kitchen with pagination.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        db: Database session dependency.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        List of appliances with device type information.

    Example:
        GET /kitchens/123/appliances?skip=0&limit=50
    """
    try:
        return crud_device.get_kitchen_appliances(db, kitchen_id, skip=skip, limit=limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@appliances_router.get(
    "/{kitchen_id}/appliances/search",
    response_model=list[ApplianceWithDeviceType],
    summary="Search kitchen appliances"
)
def search_kitchen_appliances(
        kitchen_id: int,
        db: Annotated[Session, Depends(get_db)],
        device_type_id: int | None = Query(None, gt=0, description="Filter by device type"),
        brand: str | None = Query(None, description="Filter by brand"),
        smart: bool | None = Query(None, description="Filter by smart capability"),
        available: bool | None = Query(None, description="Filter by availability"),
        min_power_watts: float | None = Query(None, gt=0, description="Minimum power consumption in watts"),
        max_power_watts: float | None = Query(None, gt=0, description="Maximum power consumption in watts"),
        min_power_kw: float | None = Query(None, gt=0, description="Minimum power consumption in kilowatts"),
        max_power_kw: float | None = Query(None, gt=0, description="Maximum power consumption in kilowatts"),
        min_capacity_liters: float | None = Query(None, gt=0, description="Minimum capacity"),
        max_capacity_liters: float | None = Query(None, gt=0, description="Maximum capacity")
) -> list[ApplianceWithDeviceType]:
    """Search appliances by various criteria.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        db: Database session dependency.
        device_type_id: Optional device type filter.
        brand: Optional brand filter.
        smart: Optional smart capability filter.
        available: Optional availability filter.
        min_power_watts: Optional minimum power filter in watts.
        max_power_watts: Optional maximum power filter in watts.
        min_power_kw: Optional minimum power filter in kilowatts.
        max_power_kw: Optional maximum power filter in kilowatts.
        min_capacity_liters: Optional minimum capacity filter.
        max_capacity_liters: Optional maximum capacity filter.

    Returns:
        List of appliances matching the search criteria.

    Example:
        GET /kitchens/123/appliances/search?min_power_kw=2.0&max_power_kw=5.0&smart=true
    """
    try:
        search_params = ApplianceSearchParams(
            device_type_id=device_type_id,
            brand=brand,
            smart=smart,
            available=available,
            min_power_watts=min_power_watts,
            max_power_watts=max_power_watts,
            min_power_kw=min_power_kw,
            max_power_kw=max_power_kw,
            min_capacity_liters=min_capacity_liters,
            max_capacity_liters=max_capacity_liters
        )
        return crud_device.search_appliances(db, kitchen_id, search_params)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@appliances_router.get(
    "/{kitchen_id}/appliances/{appliance_id}",
    response_model=ApplianceWithDeviceType,
    summary="Get appliance by ID"
)
def get_appliance(
        kitchen_id: int,
        appliance_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> ApplianceWithDeviceType:
    """Get a specific appliance by ID.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        appliance_id: The unique identifier of the appliance.
        db: Database session dependency.

    Returns:
        The appliance details with device type information.

    Raises:
        HTTPException: 404 if appliance not found or doesn't belong to kitchen.

    Example:
        GET /kitchens/123/appliances/456
    """
    try:
        appliance = crud_device.get_appliance_by_id(db, appliance_id, kitchen_id)
        if not appliance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appliance with ID {appliance_id} not found in kitchen {kitchen_id}"
            )
        return appliance
    except ValueError as e:
        if "does not belong" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@appliances_router.put(
    "/{kitchen_id}/appliances/{appliance_id}",
    response_model=ApplianceWithDeviceType,
    summary="Update appliance"
)
def update_appliance(
        kitchen_id: int,
        appliance_id: int,
        appliance_data: ApplianceUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> ApplianceWithDeviceType:
    """Update an existing appliance.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        appliance_id: The unique identifier of the appliance.
        appliance_data: Updated appliance data.
        db: Database session dependency.

    Returns:
        The updated appliance with device type information.

    Raises:
        HTTPException: 404 if appliance not found, 400 if validation fails.

    Example:
        ```json
        {
            "name": "Updated Oven Name",
            "available": false,
            "power_kw": 4.0
        }
        ```
    """
    try:
        return crud_device.update_appliance(db, appliance_id, kitchen_id, appliance_data)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@appliances_router.delete(
    "/{kitchen_id}/appliances/{appliance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appliance"
)
def delete_appliance(
        kitchen_id: int,
        appliance_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete an appliance.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        appliance_id: The unique identifier of the appliance.
        db: Database session dependency.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if appliance not found or doesn't belong to kitchen.

    Example:
        DELETE /kitchens/123/appliances/456
    """
    try:
        crud_device.delete_appliance(db, appliance_id, kitchen_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ================================================================== #
# Kitchen Tool Routes                                                #
# ================================================================== #

@tools_router.post(
    "/{kitchen_id}/tools",
    response_model=KitchenToolWithDeviceType,
    status_code=status.HTTP_201_CREATED,
    summary="Create kitchen tool"
)
def create_kitchen_tool(
        kitchen_id: int,
        tool_data: KitchenToolCreate,
        db: Annotated[Session, Depends(get_db)]
) -> KitchenToolWithDeviceType:
    """Create a new kitchen tool.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        tool_data: Tool data to create.
        db: Database session dependency.

    Returns:
        The created tool with device type information.

    Raises:
        HTTPException: 400 if validation fails.

    Example:
        ```json
        {
            "name": "Chef's Knife",
            "device_type_id": 2,
            "material": "stainless steel",
            "size_or_detail": "8 inch",
            "quantity": 1
        }
        ```
    """
    try:
        return crud_device.create_kitchen_tool(db, kitchen_id, tool_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tools_router.get(
    "/{kitchen_id}/tools",
    response_model=list[KitchenToolWithDeviceType],
    summary="Get kitchen tools"
)
def get_kitchen_tools(
        kitchen_id: int,
        db: Annotated[Session, Depends(get_db)],
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> list[KitchenToolWithDeviceType]:
    """Get all kitchen tools with pagination.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        db: Database session dependency.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        List of tools with device type information.

    Example:
        GET /kitchens/123/tools?skip=0&limit=50
    """
    try:
        return crud_device.get_kitchen_tools(db, kitchen_id, skip=skip, limit=limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tools_router.get(
    "/{kitchen_id}/tools/search",
    response_model=list[KitchenToolWithDeviceType],
    summary="Search kitchen tools"
)
def search_kitchen_tools(
        kitchen_id: int,
        db: Annotated[Session, Depends(get_db)],
        device_type_id: int | None = Query(None, gt=0, description="Filter by device type"),
        material: str | None = Query(None, description="Filter by material"),
        available: bool | None = Query(None, description="Filter by availability"),
        min_quantity: int | None = Query(None, ge=1, description="Minimum quantity"),
        is_set: bool | None = Query(None, description="Filter by whether it's a set (quantity > 1)")
) -> list[KitchenToolWithDeviceType]:
    """Search kitchen tools by various criteria.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        db: Database session dependency.
        device_type_id: Optional device type filter.
        material: Optional material filter.
        available: Optional availability filter.
        min_quantity: Optional minimum quantity filter.
        is_set: Optional filter for sets (quantity > 1).

    Returns:
        List of tools matching the search criteria.

    Example:
        GET /kitchens/123/tools/search?material=steel&is_set=false
    """
    try:
        search_params = KitchenToolSearchParams(
            device_type_id=device_type_id,
            material=material,
            available=available,
            min_quantity=min_quantity,
            is_set=is_set
        )
        return crud_device.search_kitchen_tools(db, kitchen_id, search_params)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tools_router.get(
    "/{kitchen_id}/tools/{tool_id}",
    response_model=KitchenToolWithDeviceType,
    summary="Get kitchen tool by ID"
)
def get_kitchen_tool(
        kitchen_id: int,
        tool_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> KitchenToolWithDeviceType:
    """Get a specific kitchen tool by ID.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        tool_id: The unique identifier of the tool.
        db: Database session dependency.

    Returns:
        The tool details with device type information.

    Raises:
        HTTPException: 404 if tool not found or doesn't belong to kitchen.

    Example:
        GET /kitchens/123/tools/456
    """
    try:
        tool = crud_device.get_kitchen_tool_by_id(db, tool_id, kitchen_id)
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Kitchen tool with ID {tool_id} not found in kitchen {kitchen_id}"
            )
        return tool
    except ValueError as e:
        if "does not belong" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tools_router.put(
    "/{kitchen_id}/tools/{tool_id}",
    response_model=KitchenToolWithDeviceType,
    summary="Update kitchen tool"
)
def update_kitchen_tool(
        kitchen_id: int,
        tool_id: int,
        tool_data: KitchenToolUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> KitchenToolWithDeviceType:
    """Update an existing kitchen tool.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        tool_id: The unique identifier of the tool.
        tool_data: Updated tool data.
        db: Database session dependency.

    Returns:
        The updated tool with device type information.

    Raises:
        HTTPException: 404 if tool not found, 400 if validation fails.

    Example:
        ```json
        {
            "available": false,
            "quantity": 2
        }
        ```
    """
    try:
        return crud_device.update_kitchen_tool(db, tool_id, kitchen_id, tool_data)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@tools_router.delete(
    "/{kitchen_id}/tools/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete kitchen tool"
)
def delete_kitchen_tool(
        kitchen_id: int,
        tool_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a kitchen tool.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        tool_id: The unique identifier of the tool.
        db: Database session dependency.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if tool not found or doesn't belong to kitchen.

    Example:
        DELETE /kitchens/123/tools/456
    """
    try:
        crud_device.delete_kitchen_tool(db, tool_id, kitchen_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ================================================================== #
# Summary Routes                                                     #
# ================================================================== #

@summary_router.get(
    "/{kitchen_id}/summary",
    response_model=KitchenDeviceSummary,
    summary="Get kitchen device summary"
)
def get_kitchen_device_summary(
        kitchen_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> KitchenDeviceSummary:
    """Get summary statistics for all devices in a kitchen.

    Args:
        kitchen_id: The unique identifier of the kitchen.
        db: Database session dependency.

    Returns:
        Summary statistics including counts of appliances, tools, and device types.

    Example:
        GET /kitchens/123/summary
    """
    try:
        return crud_device.get_kitchen_device_summary(db, kitchen_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ================================================================== #
# Main Router                                                        #
# ================================================================== #

router = APIRouter()
router.include_router(device_types_router)
router.include_router(appliances_router)
router.include_router(tools_router)
router.include_router(summary_router)