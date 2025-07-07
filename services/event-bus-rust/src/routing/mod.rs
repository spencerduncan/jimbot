use anyhow::Result;
use dashmap::DashMap;
use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{debug, info};

use crate::proto::{Event, EventType};

pub type EventHandler = Arc<dyn Fn(Event) + Send + Sync>;
pub type EventChannel = mpsc::UnboundedSender<Event>;

/// Topic-based event router
pub struct EventRouter {
    /// Map of topic patterns to handlers
    handlers: DashMap<String, Vec<EventHandler>>,
    /// Map of topic patterns to channels (for gRPC streaming)
    channels: DashMap<String, Vec<EventChannel>>,
}

impl Default for EventRouter {
    fn default() -> Self {
        Self::new()
    }
}

impl EventRouter {
    pub fn new() -> Self {
        Self {
            handlers: DashMap::new(),
            channels: DashMap::new(),
        }
    }

    /// Route an event to all matching subscribers
    pub async fn route_event(&self, event: Event) -> Result<()> {
        let topic = self.event_to_topic(&event);
        debug!("Routing event to topic: {}", topic);

        let mut routed_count = 0;

        // Route to handlers
        for entry in self.handlers.iter() {
            if self.matches_pattern(&topic, entry.key()) {
                for handler in entry.value() {
                    handler(event.clone());
                    routed_count += 1;
                }
            }
        }

        // Route to channels
        let mut dead_channels = Vec::new();
        for entry in self.channels.iter() {
            if self.matches_pattern(&topic, entry.key()) {
                for (idx, channel) in entry.value().iter().enumerate() {
                    if channel.send(event.clone()).is_err() {
                        dead_channels.push((entry.key().clone(), idx));
                    } else {
                        routed_count += 1;
                    }
                }
            }
        }

        // Clean up dead channels
        for (pattern, _) in dead_channels {
            self.channels.alter(&pattern, |_, mut channels| {
                channels.retain(|ch| !ch.is_closed());
                channels
            });
        }

        if routed_count == 0 {
            debug!("No subscribers for topic: {}", topic);
        } else {
            debug!("Event routed to {} subscribers", routed_count);
        }

        Ok(())
    }

    /// Subscribe a handler to a topic pattern
    pub fn subscribe_handler(&self, pattern: String, handler: EventHandler) {
        info!("Adding handler subscription for pattern: {}", pattern);
        self.handlers
            .entry(pattern)
            .or_default()
            .push(handler);
    }

    /// Subscribe a channel to a topic pattern (for gRPC streaming)
    pub fn subscribe_channel(&self, pattern: String, channel: EventChannel) {
        info!("Adding channel subscription for pattern: {}", pattern);
        self.channels
            .entry(pattern)
            .or_default()
            .push(channel);
    }

    /// Convert event to topic string
    fn event_to_topic(&self, event: &Event) -> String {
        let event_type = EventType::try_from(event.r#type).ok();
        match event_type {
            Some(EventType::GameState) => "game.state.update".to_string(),
            Some(EventType::Heartbeat) => "system.heartbeat".to_string(),
            Some(EventType::MoneyChanged) => "game.money.changed".to_string(),
            Some(EventType::ScoreChanged) => "game.score.changed".to_string(),
            Some(EventType::HandPlayed) => "game.hand.played".to_string(),
            Some(EventType::CardsDiscarded) => "game.cards.discarded".to_string(),
            Some(EventType::JokersChanged) => "game.jokers.changed".to_string(),
            Some(EventType::RoundChanged) => "game.round.changed".to_string(),
            Some(EventType::PhaseChanged) => "game.phase.changed".to_string(),
            Some(EventType::RoundComplete) => "game.round.complete".to_string(),
            Some(EventType::ConnectionTest) => "system.connection.test".to_string(),
            _ => "unknown".to_string(),
        }
    }

    /// Check if topic matches pattern (supports * wildcard)
    pub fn matches_pattern(&self, topic: &str, pattern: &str) -> bool {
        if pattern == topic {
            return true;
        }

        let pattern_parts: Vec<&str> = pattern.split('.').collect();
        let topic_parts: Vec<&str> = topic.split('.').collect();

        if pattern_parts.len() != topic_parts.len() {
            return false;
        }

        for (p, t) in pattern_parts.iter().zip(topic_parts.iter()) {
            if *p != "*" && *p != *t {
                return false;
            }
        }

        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pattern_matching() {
        let router = EventRouter::new();

        assert!(router.matches_pattern("game.state.update", "game.state.update"));
        assert!(router.matches_pattern("game.state.update", "game.*.update"));
        assert!(router.matches_pattern("game.state.update", "game.*.*"));
        assert!(router.matches_pattern("game.state.update", "*.*.*"));

        assert!(!router.matches_pattern("game.state.update", "game.state"));
        assert!(!router.matches_pattern("game.state.update", "system.*.*"));
    }
}
