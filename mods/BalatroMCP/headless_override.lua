-- BalatroMCP: Headless Override Module
-- Disables rendering and visual effects for headless operation

local HeadlessOverride = {
	enabled = false,
	original_functions = {},
}

function HeadlessOverride:enable()
	if self.enabled then
		return
	end

	-- Store original functions
	self.original_functions.draw = love.draw
	self.original_functions.graphics_present = love.graphics.present
	self.original_functions.window_isVisible = love.window.isVisible

	-- Override draw function
	love.draw = function()
		-- Do nothing - no rendering
	end

	-- Override graphics present
	love.graphics.present = function()
		-- Do nothing - no screen update
	end

	-- Make window think it's not visible
	love.window.isVisible = function()
		return false
	end

	-- Disable VSync
	love.window.setVSync(0)

	-- Override particle systems
	local ParticleSystem = love.graphics.newParticleSystem
	love.graphics.newParticleSystem = function(...)
		local ps = ParticleSystem(...)
		ps.emit = function() end
		ps.update = function() end
		ps.draw = function() end
		return ps
	end

	-- Override shader compilation (performance optimization)
	love.graphics.newShader = function()
		-- Return a dummy shader that does nothing
		return {
			send = function() end,
			sendColor = function() end,
			hasUniform = function()
				return false
			end,
		}
	end

	-- Disable sound (optional, can be configured)
	if BalatroMCP and BalatroMCP.config and BalatroMCP.config.disable_sound then
		love.audio.setVolume(0)
		local newSource = love.audio.newSource
		love.audio.newSource = function(...)
			local source = newSource(...)
			source.play = function() end
			return source
		end
	end

	-- Override animation updates to run faster
	if G and G.SETTINGS then
		G.SETTINGS.GAMESPEED = 4 -- Run at 4x speed
		G.SETTINGS.FASTFORWARD = true
	end

	self.enabled = true
end

function HeadlessOverride:disable()
	if not self.enabled then
		return
	end

	-- Restore original functions
	love.draw = self.original_functions.draw
	love.graphics.present = self.original_functions.graphics_present
	love.window.isVisible = self.original_functions.window_isVisible

	-- Restore audio
	love.audio.setVolume(1)

	-- Restore game speed
	if G and G.SETTINGS then
		G.SETTINGS.GAMESPEED = 1
		G.SETTINGS.FASTFORWARD = false
	end

	self.enabled = false
end

return HeadlessOverride
