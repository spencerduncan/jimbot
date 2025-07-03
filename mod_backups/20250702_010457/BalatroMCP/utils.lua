-- BalatroMCP: Utility functions for safe state extraction
-- Provides circular reference safe methods for accessing nested table structures

local Utils = {}

-- Safe path checking utility
function Utils.safe_check_path(root, path)
    if not root then
        return false
    end

    local current = root
    for _, key in ipairs(path) do
        if type(current) ~= "table" or current[key] == nil then
            return false
        end
        current = current[key]
    end
    return true
end

-- Safe value retrieval with default fallback
function Utils.safe_get_value(table, key, default)
    if not table or type(table) ~= "table" then
        return default
    end

    if table[key] ~= nil then
        return table[key]
    end

    return default
end

-- Safe nested value retrieval with path array
function Utils.safe_get_nested_value(root, path, default)
    if not root then
        return default
    end

    local current = root
    for _, key in ipairs(path) do
        if type(current) ~= "table" or current[key] == nil then
            return default
        end
        current = current[key]
    end
    return current
end

-- CIRCULAR REFERENCE SAFE utility functions
function Utils.safe_primitive_value(table, key, default)
    -- Safely get a PRIMITIVE VALUE ONLY from a table with default fallback
    -- This prevents circular references by only returning primitive types
    if not table or type(table) ~= "table" then
        return default
    end

    local value = table[key]
    if value ~= nil then
        local value_type = type(value)
        if value_type == "string" or value_type == "number" or value_type == "boolean" then
            return value
        else
            -- Non-primitive type detected, return default to avoid circular reference
            return default
        end
    end

    return default
end

function Utils.safe_primitive_nested_value(root, path, default)
    -- Safely get a nested PRIMITIVE VALUE ONLY from a table structure
    -- This prevents circular references by only returning primitive types
    if not root then
        return default
    end

    local current = root
    for _, key in ipairs(path) do
        if type(current) ~= "table" or current[key] == nil then
            return default
        end
        current = current[key]
    end

    -- Only return if it's a primitive type
    local value_type = type(current)
    if value_type == "string" or value_type == "number" or value_type == "boolean" then
        return current
    else
        -- Non-primitive type detected, return default to avoid circular reference
        return default
    end
end

-- Card-specific utility functions
function Utils.get_card_enhancement_safe(card)
    -- Determine card enhancement with CIRCULAR REFERENCE SAFE access
    if not card then
        return "none"
    end

    local ability_name = Utils.safe_primitive_nested_value(card, { "ability", "name" }, nil)
    if ability_name and type(ability_name) == "string" then
        local enhancement_map = {
            m_bonus = "bonus",
            m_mult = "mult",
            m_wild = "wild",
            m_glass = "glass",
            m_steel = "steel",
            m_stone = "stone",
            m_gold = "gold",
        }
        return enhancement_map[ability_name] or "none"
    end
    return "none"
end

function Utils.get_card_edition_safe(card)
    -- Determine card edition with CIRCULAR REFERENCE SAFE access
    if not card then
        return "none"
    end

    if card.edition and type(card.edition) == "table" then
        -- Check each edition type as primitive boolean
        if Utils.safe_primitive_value(card.edition, "foil", false) then
            return "foil"
        elseif Utils.safe_primitive_value(card.edition, "holo", false) then
            return "holographic"
        elseif Utils.safe_primitive_value(card.edition, "polychrome", false) then
            return "polychrome"
        elseif Utils.safe_primitive_value(card.edition, "negative", false) then
            return "negative"
        end
    end
    return "none"
end

function Utils.get_card_seal_safe(card)
    -- Determine card seal with CIRCULAR REFERENCE SAFE access
    if not card then
        return "none"
    end

    local seal = Utils.safe_primitive_value(card, "seal", "none")
    return seal
end

return Utils
