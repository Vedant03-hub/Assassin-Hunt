# Game Architecture & Flow Diagrams

This file contains Mermaid diagrams showing the game loop flowchart and a component architecture overview.

## Game Loop Flowchart

```mermaid
flowchart TD
  Start[Start / Menu]
  Play[Start Game]
  Input[Process Input]
  Update[Update Entities (Player, Enemies, Bullets, Particles)]
  Collisions[Handle Collisions & Combat]
  AI[Enemy AI: Patrol -> Detect -> Chase -> Search]
  Render[Render World, Entities, HUD]
  CheckGameOver{Player Dead?}
  End[Game Over / Return to Menu]

  Start --> Play
  Play --> Input
  Input --> Update
  Update --> AI
  AI --> Collisions
  Collisions --> Render
  Render --> CheckGameOver
  CheckGameOver -- No --> Input
  CheckGameOver -- Yes --> End
```

## Component Diagram (High-level)

```mermaid
graph LR
  subgraph Frontend["Rendering & Input"]
    Renderer[Renderer (Pygame)]
    Input[Input Handler (Keyboard & Mouse)]
  end

  subgraph GameLoop["Game Loop"]
    Loop[Main Loop]
    State[Game State (menu/playing/gameover)]
  end

  subgraph Gameplay["Gameplay Systems"]
    PlayerSystem[Player (movement, weapons, health)]
    EnemySystem[Enemy AI (vision, patrol, chase)]
    Physics[Collision Detection]
    Combat[Combat & Damage]
    Particles[Particles/Effects]
  end

  subgraph Data["Game Data"]
    Entities[Entities List (player, enemies, bullets, particles)]
    Config[Config / Constants]
  end

  subgraph World["World"]
    Obstacles[Obstacles / Cover]
  end

  Renderer --> Loop
  Input --> Loop
  Loop --> PlayerSystem
  Loop --> EnemySystem
  Loop --> Physics
  Loop --> Combat
  Loop --> Particles
  PlayerSystem --> Entities
  EnemySystem --> Entities
  Physics --> Entities
  Combat --> Entities
  Entities --> Renderer
  Obstacles --> Physics
  Config --> Loop
  State --> Loop
```

Legend:
- Renderer & Input: Pygame window and event processing.
- Game Loop: central update-render cycle.
- Gameplay Systems: player controls, enemy AI, collision and combat, VFX.
- World: cover obstacles affect line-of-sight.
- Data: runtime entity lists and tunable constants.