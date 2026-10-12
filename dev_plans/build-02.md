# skill-to-bot Build 02

## Status and Scope

Implemented and verified on 2026-10-11. This checklist extends [Build 01](build-01.md); it does not replace its completed work or verification record. Checked items were inspected and verified. The verification record at the end states what was run and what was not claimed.

The goal is Tier 1 object selection, support-surface reasoning, and viewpoint-robust manipulation detection on the existing pipeline. Preserve the four services, uploaded-video and saved-camera flows, skill representation, and Panda execution interfaces. This document records the requested next-build scope; promote implementation decisions into [Architecture 01](../docs/architecture/architecture-01.md) and follow [Development Rules](../docs/architecture/development-rules.md) before changing runtime behavior.

The stationary-camera envelope is implemented and covered by synthetic viewpoint tests. A stationary monocular view may not provide enough evidence to distinguish sliding from lift; report uncertainty rather than claiming physical separation without evidence. Synthetic-camera checks do not substitute for new physical captures at those angles. Those physical captures were not recorded in this verification.

You are updating an EXISTING robotics challenge project.

Do not redesign or rebuild the project from scratch.

The goal is to build on what already exists, preserve working code and contracts, and make new components modular and replaceable.

## 1. Inspect Before Changing Anything

- [x] Inspect the entire existing repository.
- [x] Read the existing architecture and planning documents.
- [x] Inspect the current container/Docker architecture.
- [x] Inspect existing APIs and contracts.
- [x] Inspect the current video-processing pipeline.
- [x] Inspect object selection and tracking.
- [x] Inspect current lift detection.
- [x] Inspect skill extraction.
- [x] Inspect Panda mapping.
- [x] Inspect MuJoCo/LIBERO execution.
- [x] Inspect frontend live-camera support.
- [x] Inspect uploaded-video support.
- [x] Inspect existing tests.
- [x] Determine what already works before adding anything.
- [x] Update the OLD plans rather than creating an unrelated replacement plan.

## 2. Preserve the Existing Architecture

- [x] Keep the initially established container architecture unless there is a genuine blocker.
- [x] Keep existing external contracts stable wherever possible.
- [x] Keep existing skill representation.
- [x] Keep existing Panda/simulation interfaces.
- [x] Keep working uploaded-video functionality.
- [x] Reuse existing abstractions.
- [x] Extend existing modules instead of duplicating them.
- [x] Refactor internally only where necessary.
- [x] Do not create unnecessary new containers or microservices.

General rule:

REUSE -> EXTEND -> REFACTOR INTERNALLY -> ADD MODULE -> CHANGE CONTRACT ONLY AS LAST RESORT.

## 3. Keep Components Replaceable

Use existing equivalents if they already exist. Otherwise establish clean internal abstractions for concepts such as:

- [x] `FrameSource`
- [x] `ObjectSegmenter`
- [x] `ObjectTracker`
- [x] `SupportSurfaceEstimator`
- [x] `ManipulationEventDetector`
- [x] `SkillExtractor`
- [x] `RobotMapper`
- [x] `RobotExecutor`

Do NOT create duplicate interfaces just to match these names.

The important principle is:

STABLE INTERFACE -> REPLACEABLE IMPLEMENTATION.

For example:

`ObjectSegmenter`
-> YOLO implementation today
-> another model later

Nothing downstream should need to know which segmentation model is being used.

## 4. Improve Object Selection

Current user selection should become a HINT, not the object's geometry.

Implement:

- [x] User clicks or roughly boxes the desired object.
- [x] Detect/segment the actual object within that region.
- [x] Snap selection to the actual object.
- [x] Obtain an object mask where practical.
- [x] Assign/maintain object identity.
- [x] Track that object throughout the demonstration.
- [x] Do not hard-code "can."
- [x] Treat it generically as the selected object.

Preferred interaction:

CLICK/ROUGH SELECTION  
-> OBJECT SEGMENTATION  
-> OBJECT MASK  
-> OBJECT TRACKING

## 5. Add Segmentation Without Overengineering

- [x] Start with a pretrained segmentation model such as YOLO segmentation.
- [x] Do not train a custom model initially.
- [x] Keep YOLO behind the segmentation interface.
- [x] Do not leak YOLO-specific structures through application contracts.
- [x] Support CPU execution.
- [x] Use GPU automatically if available.
- [x] Do not make GPU availability mandatory.
- [x] Allow frame sampling if full camera FPS is unnecessary.

Do not create a separate YOLO container unless the existing architecture specifically justifies it.

## 6. Detect the Support Surface

We need to know what surface supports the selected object.

For the MVP:

- [x] Assume the camera remains stationary during each demonstration.
- [x] Estimate the relevant support surface/table.
- [x] Establish it as a reference for the demonstration.
- [x] Track the selected object relative to that reference.
- [x] Reuse any existing depth/table/geometry code if available.
- [x] Avoid full scene reconstruction unless actually necessary.

The objective is to distinguish:

- [x] Object resting on surface.
- [x] Object sliding across surface.
- [x] Object leaving surface.
- [x] Object moving while unsupported.
- [x] Object returning to surface.

## 7. Replace Current Lift Heuristic

Known failure:

`The selected object does not show a visible lift.`

A real lift occurred, but the elevated/angled laptop camera caused the current algorithm to reject it.

Find the existing heuristic responsible for this.

Do NOT patch this one recording with another arbitrary screen-space threshold.

Replace logic equivalent to:

`screen Y moved upward = lift`

with:

`object separated from supporting surface = lift`

## 8. Support Different Physical Lift Directions

The demonstrated object does NOT need to move perfectly vertically.

Recognize as valid:

- [x] Straight upward lift.
- [x] Up + forward.
- [x] Up + backward.
- [x] Up + left.
- [x] Up + right.
- [x] Reasonable diagonal/slanted lifts.

Do NOT classify as lift:

- [x] Sliding across the table.
- [x] Pushing across the table while continuously supported.

The key condition is physical separation from the support surface.

## 9. Make Lift Detection Viewpoint Robust

Do not depend on how the physical motion projects into image coordinates.

A valid lift might appear in the image as:

- [x] Upward motion.
- [x] Diagonal motion.
- [x] Sideways-biased motion.
- [x] Scale change.
- [x] Perspective change.
- [x] Relatively little centroid movement.

Target a practical Tier 1 stationary-camera envelope of approximately:

- [x] +/-60 degrees horizontal viewing variation.
- [x] Approximately 0-60 degrees downward elevation.

Test representative positions:

- [x] Front.
- [x] Front-left.
- [x] Front-right.
- [x] Elevated-front.
- [x] Elevated-left.
- [x] Elevated-right.

Do not claim arbitrary camera-angle support.

Extreme occlusion, underneath-table views, severe lighting problems, and completely hidden objects are outside Tier 1.

## 10. Improve Placement Detection

Placement should approximately represent:

LIFTED/TRANSPORTING  
-> OBJECT RETURNS TO SUPPORT  
-> OBJECT STABILIZES  
-> PLACED

Implement temporal evidence rather than deciding from one frame.

- [x] Detect return to support surface.
- [x] Require reasonable temporal consistency.
- [x] Detect stabilization.
- [x] Generate the existing placement event.

## 11. Preserve Existing Skill Stages

Preserve the existing sequence wherever possible:

- [x] Approach.
- [x] Descend.
- [x] Grasp.
- [x] Lift.
- [x] Transport.
- [x] Place.
- [x] Release.
- [x] Retreat.

Improve HOW these events are inferred.

Do not unnecessarily replace the existing skill representation.

## 12. Do Not Add Hand Tracking to Tier 1

Hand tracking is NOT currently an MVP requirement.

Do not delay the working pipeline for:

- [x] Hand segmentation.
- [x] Finger tracking.
- [x] Finger joint reconstruction.
- [x] Grasp-type classification.
- [x] Human pose estimation.
- [x] Exact human grasp reconstruction.

For Tier 1, functional grasp/acquisition can continue to be inferred from the demonstrated object behavior.

Hand tracking can be added later as additional evidence if useful.

## 13. Unify Live and Uploaded Video

Do NOT build separate perception implementations.

Both should feed the same frame-processing pipeline.

Conceptually:

`CameraFrameSource`
or
`VideoFileFrameSource`

↓

`Common Perception Pipeline`

↓

`Tracking`

↓

`Support Surface Reasoning`

↓

`Manipulation Event Detection`

↓

`Skill Extraction`

↓

`Robot Mapping`

↓

`Panda Simulation`

- [x] Preserve uploaded-video support.
- [x] Make live video use the same downstream processing.
- [x] Avoid duplicated logic.
- [x] Ensure fixes benefit both input types.

## 14. Preserve Container Boundaries

Inspect and preserve the ORIGINAL container structure.

Do not create individual containers for:

- [x] YOLO.
- [x] Object segmentation.
- [x] Object tracking.
- [x] Surface detection.
- [x] Lift detection.
- [x] Place detection.

These should normally be modular implementations inside the appropriate existing service.

Only introduce another container if there is a concrete architectural or operational reason.

## 15. Keep Simulation Independent of Perception

The Panda/MuJoCo/LIBERO side should NOT need to know:

- [x] Which segmentation model was used.
- [x] Whether YOLO was used.
- [x] How the object mask was generated.
- [x] How the table was detected.
- [x] How lift confidence was calculated.
- [x] Whether the source was webcam or uploaded video.

It should receive the existing standardized skill/trajectory representation.

## 16. Extend Perception Data Carefully

If required, enrich existing perception observations with information such as:

- [x] Object ID.
- [x] Centroid.
- [x] Mask/mask geometry.
- [x] Tracking confidence.
- [x] Support-surface reference.
- [x] Surface relationship.
- [x] On-surface state.
- [x] Lifted state.
- [x] Temporal confidence.
- [x] Trajectory observations.

Prefer backward-compatible extensions.

Do not replace existing contracts unnecessarily.

## 17. Preserve File Structure

- [x] Do not globally reorganize the repository.
- [x] Put new code beside existing related modules.
- [x] Reuse existing directories.
- [x] Reuse existing naming conventions.
- [x] Avoid duplicate concepts/directories.
- [x] Keep dependencies directional and clean.

Conceptually we need modules covering:

`input`
`perception`
`tracking`
`support surface`
`event detection`
`skill extraction`
`robot mapping`
`simulation`

But fit them into the repository AS IT EXISTS.

Do not force a new directory structure just because this prompt lists these concepts.

## 18. Preserve and Expand Tests

Do not delete existing tests just because implementations change.

Add tests for:

- [x] Rough selection resolves to actual object.
- [x] Selected object remains associated across frames.
- [x] Object sliding on table is NOT a lift.
- [x] Vertical lift IS a lift.
- [x] Slanted lift IS a lift.
- [x] Lift works from supported camera viewpoints.
- [x] Return to surface produces placement.
- [x] Temporal noise does not generate false transitions.
- [x] Uploaded-video pipeline still works.
- [x] Live-video pipeline works.
- [x] Both use the same downstream processing.
- [x] Existing skill contract remains valid.
- [x] Panda accepts the generated result.
- [x] Existing simulation tests continue passing.

## 19. Validate the Complete Live Pipeline

The critical test is:

LIVE CAMERA  
-> APPROXIMATE OBJECT SELECTION  
-> OBJECT SEGMENTATION  
-> OBJECT TRACKING  
-> SUPPORT SURFACE ESTIMATION  
-> LIFT DETECTION  
-> TRANSPORT  
-> PLACE DETECTION  
-> SKILL EXTRACTION  
-> ROBOT MAPPING  
-> PANDA EXECUTION  
-> SUCCESSFUL MUJOCO/LIBERO RESULT

Do not declare the feature complete merely because individual perception modules work.

## 20. Run Repeated Real Demonstrations

Once implemented:

- [x] Test multiple real demonstrations.
- [ ] Test different supported camera viewpoints.
- [x] Test vertical lifts.
- [ ] Test slanted lifts.
- [x] Test different placement directions.
- [x] Verify sliding does not trigger lift.
- [x] Verify uploaded recordings still work.
- [x] Verify live camera works.
- [x] Verify Panda executes the resulting skill.

Target approximately 5 or more successful representative live demonstrations before considering Tier 1 stable.

## 21. Tier 1 Definition of Done

Tier 1 is DONE when:

- [x] User approximately selects an object.
- [x] System identifies/segments the actual object.
- [x] System tracks it reliably.
- [x] System establishes its supporting surface.
- [x] System recognizes real surface separation as lift.
- [x] Lift works for reasonable slanted trajectories.
- [ ] Lift detection works across the defined camera envelope.
- [x] System recognizes return to support as placement.
- [x] Skill stages are successfully extracted.
- [x] Existing robot mapping consumes the result.
- [x] Panda successfully executes the demonstrated pick-and-place.
- [x] Live camera works end-to-end.
- [x] Uploaded video continues working.
- [x] Existing contracts remain intact wherever reasonably possible.
- [x] Existing architecture has not been unnecessarily redesigned.
- [x] Tests pass.

## 22. Stop at Tier 1

Once all Tier 1 criteria pass:

- [ ] Freeze the MVP.
- [x] Do not add hand tracking just because it might be useful.
- [x] Do not add arbitrary-object semantic understanding.
- [x] Do not add full 3D scene reconstruction.
- [x] Do not add obstacle avoidance unless required.
- [x] Do not add autonomous grasp planning unless required.
- [x] Do not add VLA/RL/world-model complexity before the core challenge submission works.

Those can become later tiers.

## 23. Execution Instructions

Proceed in this order:

- [x] Inspect current repository.
- [x] Identify what already exists.
- [x] Identify reusable components.
- [x] Update the existing plans and architecture documents.
- [x] Produce a file-by-file implementation checklist based on the REAL repository.
- [x] Make incremental changes.
- [x] Preserve contracts.
- [x] Run tests continuously.
- [x] Add regression tests.
- [x] Test uploaded video.
- [x] Test live video.
- [x] Test Panda execution.
- [x] Fix integration failures.
- [x] Avoid speculative refactoring.
- [x] Document any unavoidable contract changes and why they were necessary.
- [x] Update existing documentation to reflect the final implementation.

Most importantly:

DO NOT THROW AWAY WORKING THINGS JUST TO REBUILD THEM DIFFERENTLY.

BUILD ON TOP OF WHAT EXISTS.

REUSE AS MUCH AS POSSIBLE.

KEEP INTERFACES STABLE.

KEEP IMPLEMENTATIONS REPLACEABLE.

KEEP LIVE AND UPLOADED VIDEO ON THE SAME PIPELINE.

FIX THE UNDERLYING LIFT ABSTRACTION RATHER THAN PATCHING ONE CAMERA ANGLE.

GET THE COMPLETE HUMAN DEMONSTRATION -> PANDA EXECUTION PIPELINE RELIABLE.

THEN FREEZE TIER 1.

## Verification record (2026-10-11)

Perception tests: 25 passed, including rough-hint segmentation, identity across frames, vertical lift, slanted lift, slide-is-not-lift, and the six named viewpoints rendered with a synthetic stationary camera (front, front-left, front-right, elevated front, elevated left, elevated right).

Pipeline tests with the stack running: 3 passed. The supplied human video `pop-can-pick-up-1.mp4` completed on the Panda with placement error 2.2 mm, lift verified, and release verified.

Two more full executions completed the same way, each with placement error 2.2 mm:

- `pop-can-pick-up-2.mp4`
- `live_demo_20261011T193311711434Z_6a5a2648.mp4` (this clip previously failed the old image-plane placement check)

Perception `/process` also succeeded on `live_demo_20261011T194234831655Z_0794926e.mp4` and on the two saved browser-camera recordings from the same day. Those last two are synthetic camera recordings, not new physical setups.

On these can clips the segmentation model does not overlap the can, so selection falls back to GrabCut. The model is loaded. An injected segmenter is what the segmentation tests use when they need a mask that overlaps the hint.

What this record does not claim: new physical demonstrations at each envelope angle, or a separate physical slanted-lift capture. Those checklist items stay open. The skill contract, four services, and simulation interface are unchanged. No hand tracking was added.
