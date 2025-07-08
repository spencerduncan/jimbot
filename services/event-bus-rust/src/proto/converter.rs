use anyhow::{anyhow, Result};
use chrono::Utc;
use uuid::Uuid;

use crate::api::models::JsonEvent;
use crate::proto::{event, Event, EventType};

/// Convert JSON event from BalatroMCP to Protocol Buffer event
pub fn json_to_proto_event(json_event: JsonEvent) -> Result<Event> {
    // Validate required fields are not empty
    if json_event.event_type.is_empty() {
        return Err(anyhow!("Event type cannot be empty"));
    }
    if json_event.source.is_empty() {
        return Err(anyhow!("Event source cannot be empty"));
    }

    let event_type = match json_event.event_type.as_str() {
        "GAME_STATE" => EventType::GameState as i32,
        "HEARTBEAT" => EventType::Heartbeat as i32,
        "MONEY_CHANGED" => EventType::MoneyChanged as i32,
        "SCORE_CHANGED" => EventType::ScoreChanged as i32,
        "HAND_PLAYED" => EventType::HandPlayed as i32,
        "CARDS_DISCARDED" => EventType::CardsDiscarded as i32,
        "JOKERS_CHANGED" => EventType::JokersChanged as i32,
        "ROUND_CHANGED" => EventType::RoundChanged as i32,
        "PHASE_CHANGED" => EventType::PhaseChanged as i32,
        "ROUND_COMPLETE" => EventType::RoundComplete as i32,
        "CONNECTION_TEST" => EventType::ConnectionTest as i32,
        _ => return Err(anyhow!("Unknown event type: {}", json_event.event_type)),
    };

    let timestamp = json_event
        .timestamp
        .unwrap_or_else(|| Utc::now().timestamp_millis());

    let mut proto_event = Event {
        event_id: Uuid::new_v4().to_string(),
        timestamp,
        r#type: event_type,
        source: json_event.source,
        version: json_event.version.unwrap_or(1),
        payload: None,
        metadata: json_event.headers.unwrap_or_default(),
        ..Default::default()
    };

    // Convert payload based on event type
    proto_event.payload = match EventType::try_from(event_type).ok() {
        Some(EventType::GameState) => Some(event::Payload::GameState(parse_game_state(
            json_event.payload,
        )?)),
        Some(EventType::Heartbeat) => Some(event::Payload::Heartbeat(parse_heartbeat(
            json_event.payload,
        )?)),
        Some(EventType::MoneyChanged) => Some(event::Payload::MoneyChanged(parse_money_changed(
            json_event.payload,
        )?)),
        Some(EventType::ConnectionTest) => Some(event::Payload::ConnectionTest(
            parse_connection_test(json_event.payload)?,
        )),
        // TODO: Implement other event type parsers
        _ => None,
    };

    Ok(proto_event)
}

use crate::proto::{
    ConnectionTestEvent, GamePhase, GameStateEvent, HeartbeatEvent, MoneyChangedEvent,
};

fn parse_game_state(payload: serde_json::Value) -> Result<GameStateEvent> {
    // Basic parsing - expand as needed
    let mut game_state = GameStateEvent {
        in_game: payload
            .get("in_game")
            .and_then(|v| v.as_bool())
            .unwrap_or(false),
        game_id: payload
            .get("game_id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        ante: payload.get("ante").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
        round: payload.get("round").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
        hand_number: payload
            .get("hand_number")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
        chips: payload.get("chips").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
        mult: payload.get("mult").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
        money: payload.get("money").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
        hand_size: payload
            .get("hand_size")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
        hands_remaining: payload
            .get("hands_remaining")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
        discards_remaining: payload
            .get("discards_remaining")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
        // Initialize with defaults
        jokers: vec![],
        hand: vec![],
        deck: None,
        consumables: vec![],
        shop_items: std::collections::HashMap::new(),
        game_state: GamePhase::PhaseUnspecified as i32,
        ui_state: String::new(),
        blind: None,
        frame_count: 0,
        score_history: std::collections::HashMap::new(),
        changes: vec![],
        initial: false,
        debug: false,
    };

    // Parse game_state/phase if present
    if let Some(phase_str) = payload.get("game_state").and_then(|v| v.as_str()) {
        game_state.game_state = match phase_str {
            "MENU" => GamePhase::PhaseMenu as i32,
            "BLIND_SELECT" => GamePhase::PhaseBlindSelect as i32,
            "SHOP" => GamePhase::PhaseShop as i32,
            "PLAYING" => GamePhase::PhasePlaying as i32,
            "GAME_OVER" => GamePhase::PhaseGameOver as i32,
            _ => GamePhase::PhaseUnspecified as i32,
        };
    }

    if let Some(ui_state) = payload.get("ui_state").and_then(|v| v.as_str()) {
        game_state.ui_state = ui_state.to_string();
    }

    Ok(game_state)
}

fn parse_heartbeat(payload: serde_json::Value) -> Result<HeartbeatEvent> {
    Ok(HeartbeatEvent {
        version: payload
            .get("version")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
        uptime: payload.get("uptime").and_then(|v| v.as_i64()).unwrap_or(0),
        headless: payload
            .get("headless")
            .and_then(|v| v.as_bool())
            .unwrap_or(false),
        game_state: payload
            .get("game_state")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
    })
}

fn parse_money_changed(payload: serde_json::Value) -> Result<MoneyChangedEvent> {
    Ok(MoneyChangedEvent {
        old_value: payload
            .get("old_value")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
        new_value: payload
            .get("new_value")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
        difference: payload
            .get("difference")
            .and_then(|v| v.as_i64())
            .unwrap_or(0) as i32,
    })
}

fn parse_connection_test(payload: serde_json::Value) -> Result<ConnectionTestEvent> {
    Ok(ConnectionTestEvent {
        message: payload
            .get("message")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string(),
    })
}
