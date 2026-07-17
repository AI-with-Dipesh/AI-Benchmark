# Automation Architecture — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Overview

Sprint 15 adds an automation layer on top of the existing AI-Benchmark engine.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   CLI       │    │   REST API  │    │  CI/CD      │
│ automation  │    │ /automation │    │ webhooks    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                  ┌───────▼────────┐
                  │ AutomationManager │
                  └───────┬────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │ Scheduler │  │ ModelSync │  │ Regression│
    │           │  │ Service   │  │ Detector  │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                  ┌───────▼────────┐
                  │ BenchEngine    │
                  └────────────────┘
