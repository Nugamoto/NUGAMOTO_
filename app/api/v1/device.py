"""FastAPI router exposing the device management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import device as crud_device
from app.schemas.device import (
    DeviceTypeCreate, DeviceTypeRead, DeviceTypeUpdate,
    ApplianceCreate, ApplianceRead, ApplianceUpdate, ApplianceWithDeviceType,
    KitchenToolCreate, KitchenToolRead, KitchenToolUpdate, KitchenToolWithDeviceType,
    ApplianceSearchParams, KitchenToolSearchParams, KitchenDeviceSummary
)

# ================================================================== #
# Sub-routers for better organization                               #
# ================================================================== #

device_types_router = APIRouter(prefix="/device-types", tags=["Device Types"])
appliances_router = APIRouter(prefix="/kitchens/{kitchen_id}/appliances", tags=["Appliances"])
tools_router = APIRouter(prefix="/kitchens/{kitchen_id}/tools", tags=["Kitchen Tools"])
summary_router = APIRouter(prefix="/kitchens/{kitchen_id}/devices", tags=["Device Summary"])


# ================================================================== #
# Device Type Management Routes                                     #
# ================================================================== #

@device_types_router.post(
    "/",
    response_model=DeviceTypeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create device type"
)
def create_device_type(
        device_type_data: DeviceTypeCreate,
        db: Session = Depends(get_db)
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
        return crud_device.create_device_type(db, device_type_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc


@device_types_router.get(
    "/",
    response_model=list[DeviceTypeRead],
    status_code=status.HTTP_200_OK,
    summary="Get all device types"
)
def get_all_device_types(
        category: str | None = Query(None, description="Filter by category"),
        db: Session = Depends(get_db)
) -> list[DeviceTypeRead]:
    """Get all device types with optional category filtering.

    Args:
        category: Optional category filter (e.g., 'appliance', 'tool').
        db: Database session dependency.

    Returns:
        List of device types, optionally filtered by category.
    """
    if category:
        return crud_device.get_device_types_by_category(db, category)
    return crud_device.get_all_device_types(db)


@device_types_router.get(
    "/{device_type_id}",
    response_model=DeviceTypeRead,
    status_code=status.HTTP_200_OK,
    summary="Get device type by ID"
)
def get_device_type(
        device_type_id: int,
        db: Session = Depends(get_db)
) -> DeviceTypeRead:
    """Get a device type by ID.

    Args:
        device_type_id: Primary key of the device type.
        db: Database session dependency.

    Returns:
        The requested device type.

    Raises:
        HTTPException: 404 if the device type does not exist.
    """
    device_type = crud_device.get_device_type_by_id(db, device_type_id)
    if device_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device type not found"
        )
    return device_type


@device_types_router.patch(
    "/{device_type_id}",
    response_model=DeviceTypeRead,
    status_code=status.HTTP_200_OK,
    summary="Update device type"
)
def update_device_type(
        device_type_id: int,
        device_type_data: DeviceTypeUpdate,
        db: Session = Depends(get_db)
) -> DeviceTypeRead:
    """Update an existing device type.

    Args:
        device_type_id: Primary key of the device type.
        device_type_data: Partial device type data for updates.
        db: Database session dependency.

    Returns:
        The updated device type.

    Raises:
        HTTPException:
            * 404 – if the device type does not exist.
            * 400 – if name conflict occurs.
    """
    try:
        device_type = crud_device.update_device_type(db, device_type_id, device_type_data)
        if device_type is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device type not found"
            )
        return device_type
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc


@device_types_router.delete(
    "/{device_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete device type"
)
def delete_device_type(
        device_type_id: int,
        db: Session = Depends(get_db)
) -> Response:
    """Delete a device type.

    Args:
        device_type_id: Primary key of the device type.
        db: Database session dependency.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException:
            * 404 – if the device type does not exist.
            * 400 – if the device type is in use.
    """
    try:
        deleted = crud_device.delete_device_type(db, device_type_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device type not found"
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc


# ================================================================== #
# Appliance Management Routes                                       #
# ================================================================== #

@appliances_router.post(
    "/",
    response_model=ApplianceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create appliance"
)
def create_appliance(
        kitchen_id: int,
        appliance_data: ApplianceCreate,
        db: Session = Depends(get_db)
) -> ApplianceRead:
    """Create a new appliance in a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        appliance_data: Appliance data to create.
        db: Database session dependency.

    Returns:
        The created appliance.

    Raises:
        HTTPException:
            * 404 – if kitchen or device type not found.
            * 400 – for validation errors.
    """
    try:
        return crud_device.create_appliance(db, kitchen_id, appliance_data)
    except ValueError as exc:
        error_msg = str(exc)
        if "Kitchen not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kitchen not found"
            ) from exc
        elif "Device type not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device type not found"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from exc


@appliances_router.get(
    "/",
    response_model=list[ApplianceWithDeviceType],
    status_code=status.HTTP_200_OK,
    summary="Get kitchen appliances"
)
def get_kitchen_appliances(
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> list[ApplianceWithDeviceType]:
    """Get all appliances for a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Database session dependency.

    Returns:
        List of appliances with device type information.
    """
    return crud_device.get_kitchen_appliances(db, kitchen_id)


@appliances_router.post(
    "/search",
    response_model=list[ApplianceWithDeviceType],
    status_code=status.HTTP_200_OK,
    summary="Search kitchen appliances"
)
def search_kitchen_appliances(
        kitchen_id: int,
        search_params: ApplianceSearchParams,
        db: Session = Depends(get_db)
) -> list[ApplianceWithDeviceType]:
    """Search appliances in a kitchen with advanced filters.

    Args:
        kitchen_id: Primary key of the kitchen.
        search_params: Search and filter parameters.
        db: Database session dependency.

    Returns:
        List of filtered appliances with device type information.

    Example:
        ```json
        {
            "brand": "KitchenAid",
            "smart": true,
            "available": true,
            "min_power_watts": 1000,
            "max_power_watts": 2000
        }
        ```
    """
    return crud_device.search_appliances(db, kitchen_id, search_params)


@appliances_router.get(
    "/{appliance_id}",
    response_model=ApplianceRead,
    status_code=status.HTTP_200_OK,
    summary="Get appliance by ID"
)
def get_appliance(
        kitchen_id: int,
        appliance_id: int,
        db: Session = Depends(get_db)
) -> ApplianceRead:
    """Get an appliance by ID.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        appliance_id: Primary key of the appliance.
        db: Database session dependency.

    Returns:
        The requested appliance.

    Raises:
        HTTPException: 404 if the appliance does not exist.
    """
    appliance = crud_device.get_appliance_by_id(db, appliance_id)
    if appliance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found"
        )

    # Verify appliance belongs to the specified kitchen
    if appliance.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found in this kitchen"
        )

    return appliance


@appliances_router.patch(
    "/{appliance_id}",
    response_model=ApplianceRead,
    status_code=status.HTTP_200_OK,
    summary="Update appliance"
)
def update_appliance(
        kitchen_id: int,
        appliance_id: int,
        appliance_data: ApplianceUpdate,
        db: Session = Depends(get_db)
) -> ApplianceRead:
    """Update an existing appliance.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        appliance_id: Primary key of the appliance.
        appliance_data: Partial appliance data for updates.
        db: Database session dependency.

    Returns:
        The updated appliance.

    Raises:
        HTTPException: 404 if the appliance does not exist or doesn't belong to kitchen.
    """
    # First verify the appliance exists and belongs to the kitchen
    existing_appliance = crud_device.get_appliance_by_id(db, appliance_id)
    if existing_appliance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found"
        )

    if existing_appliance.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found in this kitchen"
        )

    # Proceed with update
    updated_appliance = crud_device.update_appliance(db, appliance_id, appliance_data)
    if updated_appliance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found"
        )

    return updated_appliance


@appliances_router.delete(
    "/{appliance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete appliance"
)
def delete_appliance(
        kitchen_id: int,
        appliance_id: int,
        db: Session = Depends(get_db)
) -> Response:
    """Delete an appliance.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        appliance_id: Primary key of the appliance.
        db: Database session dependency.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the appliance does not exist or doesn't belong to kitchen.
    """
    # First verify the appliance exists and belongs to the kitchen
    existing_appliance = crud_device.get_appliance_by_id(db, appliance_id)
    if existing_appliance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found"
        )

    if existing_appliance.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found in this kitchen"
        )

    # Proceed with deletion
    deleted = crud_device.delete_appliance(db, appliance_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appliance not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Kitchen Tool Management Routes                                    #
# ================================================================== #

@tools_router.post(
    "/",
    response_model=KitchenToolRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create kitchen tool"
)
def create_kitchen_tool(
        kitchen_id: int,
        tool_data: KitchenToolCreate,
        db: Session = Depends(get_db)
) -> KitchenToolRead:
    """Create a new kitchen tool.

    Args:
        kitchen_id: Primary key of the kitchen.
        tool_data: Kitchen tool data to create.
        db: Database session dependency.

    Returns:
        The created kitchen tool.

    Raises:
        HTTPException:
            * 404 – if kitchen or device type not found.
            * 400 – for validation errors.
    """
    try:
        return crud_device.create_kitchen_tool(db, kitchen_id, tool_data)
    except ValueError as exc:
        error_msg = str(exc)
        if "Kitchen not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kitchen not found"
            ) from exc
        elif "Device type not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device type not found"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from exc


@tools_router.get(
    "/",
    response_model=list[KitchenToolWithDeviceType],
    status_code=status.HTTP_200_OK,
    summary="Get kitchen tools"
)
def get_kitchen_tools(
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> list[KitchenToolWithDeviceType]:
    """Get all kitchen tools for a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Database session dependency.

    Returns:
        List of kitchen tools with device type information.
    """
    return crud_device.get_kitchen_tools(db, kitchen_id)


@tools_router.post(
    "/search",
    response_model=list[KitchenToolWithDeviceType],
    status_code=status.HTTP_200_OK,
    summary="Search kitchen tools"
)
def search_kitchen_tools(
        kitchen_id: int,
        search_params: KitchenToolSearchParams,
        db: Session = Depends(get_db)
) -> list[KitchenToolWithDeviceType]:
    """Search kitchen tools with advanced filters.

    Args:
        kitchen_id: Primary key of the kitchen.
        search_params: Search and filter parameters.
        db: Database session dependency.

    Returns:
        List of filtered kitchen tools with device type information.

    Example:
        ```json
        {
            "material": "stainless steel",
            "available": true,
            "min_quantity": 2,
            "is_set": true
        }
        ```
    """
    return crud_device.search_kitchen_tools(db, kitchen_id, search_params)


@tools_router.get(
    "/{tool_id}",
    response_model=KitchenToolRead,
    status_code=status.HTTP_200_OK,
    summary="Get kitchen tool by ID"
)
def get_kitchen_tool(
        kitchen_id: int,
        tool_id: int,
        db: Session = Depends(get_db)
) -> KitchenToolRead:
    """Get a kitchen tool by ID.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        tool_id: Primary key of the kitchen tool.
        db: Database session dependency.

    Returns:
        The requested kitchen tool.

    Raises:
        HTTPException: 404 if the tool does not exist or doesn't belong to kitchen.
    """
    tool = crud_device.get_kitchen_tool_by_id(db, tool_id)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found"
        )

    # Verify tool belongs to the specified kitchen
    if tool.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found in this kitchen"
        )

    return tool


@tools_router.patch(
    "/{tool_id}",
    response_model=KitchenToolRead,
    status_code=status.HTTP_200_OK,
    summary="Update kitchen tool"
)
def update_kitchen_tool(
        kitchen_id: int,
        tool_id: int,
        tool_data: KitchenToolUpdate,
        db: Session = Depends(get_db)
) -> KitchenToolRead:
    """Update an existing kitchen tool.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        tool_id: Primary key of the kitchen tool.
        tool_data: Partial tool data for updates.
        db: Database session dependency.

    Returns:
        The updated kitchen tool.

    Raises:
        HTTPException: 404 if the tool does not exist or doesn't belong to kitchen.
    """
    # First verify the tool exists and belongs to the kitchen
    existing_tool = crud_device.get_kitchen_tool_by_id(db, tool_id)
    if existing_tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found"
        )

    if existing_tool.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found in this kitchen"
        )

    # Proceed with update
    updated_tool = crud_device.update_kitchen_tool(db, tool_id, tool_data)
    if updated_tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found"
        )

    return updated_tool


@tools_router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete kitchen tool"
)
def delete_kitchen_tool(
        kitchen_id: int,
        tool_id: int,
        db: Session = Depends(get_db)
) -> Response:
    """Delete a kitchen tool.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        tool_id: Primary key of the kitchen tool.
        db: Database session dependency.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the tool does not exist or doesn't belong to kitchen.
    """
    # First verify the tool exists and belongs to the kitchen
    existing_tool = crud_device.get_kitchen_tool_by_id(db, tool_id)
    if existing_tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found"
        )

    if existing_tool.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found in this kitchen"
        )

    # Proceed with deletion
    deleted = crud_device.delete_kitchen_tool(db, tool_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen tool not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Device Summary and Analytics Routes                               #
# ================================================================== #

@summary_router.get(
    "/summary",
    response_model=KitchenDeviceSummary,
    status_code=status.HTTP_200_OK,
    summary="Get kitchen device summary"
)
def get_kitchen_device_summary(
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> KitchenDeviceSummary:
    """Get a summary of all devices in a kitchen.

    Provides statistics about appliances, tools, availability,
    smart devices, and device type diversity.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Database session dependency.

    Returns:
        Summary statistics for the kitchen's devices.
    """
    return crud_device.get_kitchen_device_summary(db, kitchen_id)


# ================================================================== #
# Main Router Assembly                                               #
# ================================================================== #

router = APIRouter(prefix="/devices")

# Include all sub-routers
router.include_router(device_types_router)
router.include_router(appliances_router)
router.include_router(tools_router)
router.include_router(summary_router)