-- BalatroMCP: Diagnostics Module
-- Lists all available functions in G.FUNCS for debugging

local Diagnostics = {}

function Diagnostics:list_g_funcs()
	if not G or not G.FUNCS then
		return "G.FUNCS not available"
	end

	local funcs = {}
	for k, v in pairs(G.FUNCS) do
		if type(v) == "function" then
			table.insert(funcs, k)
		end
	end

	table.sort(funcs)
	return funcs
end

function Diagnostics:send_diagnostic_event(aggregator)
	local func_list = self:list_g_funcs()

	aggregator:add_event({
		type = "DIAGNOSTIC",
		source = "BalatroMCP",
		payload = {
			available_functions = type(func_list) == "table" and func_list or { func_list },
			g_exists = G ~= nil,
			g_funcs_exists = G and G.FUNCS ~= nil,
			g_game_exists = G and G.GAME ~= nil,
			g_state = G and G.STATE and tostring(G.STATE) or "unknown",
		},
	})
end

return Diagnostics
