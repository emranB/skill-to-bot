# skill-to-bot Build 02

## Status and Scope

Initial implementation verified on 2026-10-11; real-world closure is in progress. This checklist extends [Build 01](build-01.md); it does not replace its completed work or verification record. Earlier checked items describe that initial pass, not proof that the new acceptance gates below are satisfied. Preserve the verification record and record new findings cumulatively.

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

## Real-world closure baseline

Previously verified: the initial perception, support-state, supplied-video and synthetic-camera results above remain historical evidence. Baseline rerun: perception 25 passed; orchestrator 9 passed; simulation 11 passed; root 9 passed; browser 10 passed and 2 duplicate mobile physics cases skipped. The first isolated simulation invocation failed 6 contract tests because `/contracts` was not mounted; rerunning with the contract mount passed all 11. No tests were removed.

New real-world findings reported by the operator: approximate ROI does not visibly latch onto changing object geometry, production segmentation falls back to GrabCut, and multi-turn/return-near-origin paths are oversimplified. Saved run history includes support-evidence and lost-tracking failures; retain them as evidence.

Root causes found during inspection: YOLOv8n-seg ONNX (116 detection channels, 32 prototypes, 640 input) runs on CPU with BGR-to-RGB letterboxing. Full-frame inference misses the small selected object; focused crops produce candidates. Fixed 0.2 mask/hint IoU rejects small objects inside loose hints or clicks. NMS is class-agnostic. Tracking initializes from a mask but discards it and never refreshes geometry. The UI displays the manual hint, not time-aligned tracked geometry. Extraction rejects small final horizontal displacement and reduces all observations to start/goal; mapping contains one transport target. Front-plane calibration has no forward/backward axis.

### File-by-file closure checklist

- [x] Inspect existing modules, contracts, containers, tests, CI and cumulative evidence; run baseline suites.
- [x] `object_segmentation.py`: retry focused selection crops, preserve full-frame coordinates, test decoding and candidate matching, retain observable GrabCut fallback.
- [x] `object_tracking.py`: keep target identity, periodically reacquire compatible mask geometry, reject unrelated jumps, expose geometry/provenance without model tensors.
- [x] `skill_extraction.py` and perception config: simplify ordered transport while preserving corners, reversals and excursions; reject jitter, not small net displacement.
- [x] `skill.schema.json`, `skill_to_robot.py`, API validation: optional bounded transport waypoints and explicit projected-table calibration; preserve legacy front-plane skills.
- [x] `robot_control.py`: execute every transport target with closed grasp and existing bounds; record measured waypoint convergence.
- [x] Web: show acquired geometry aligned to source playback and segmentation provenance; preserve live recording and uploaded-video workflows.
- [x] Existing tests and CI: retain previous cases, add production segmentation and ordered-path/physics regressions, run all service/root/browser checks.
- [x] Real recordings: evaluate the available labeled clips, record source/view/provenance/tracking/lift/path/placement/Panda outcome, distinguish unknown views and synthetic capture.
- [x] Record the regression matrix and residual physical-view limits; leave Tier 1 unfrozen while physical and hosted acceptance gates remain open.

### Contract decision

An optional `transport` array will carry bounded world-meter waypoints while version 1.0 start/goal skills remain valid. Legacy `front` calibration keeps world X fixed. Explicit `table` calibration maps the two image axes onto robot XY at constant safe transport height; this is an operator-selected projected path, not recovered metric depth or perspective-correct 3D. Do not silently select it or claim unsupported physical direction reconstruction. Model-specific class labels remain inside perception.

### Closure changes and regressions

YOLO preprocessing retains BGR-to-RGB conversion, 640 letterboxing, the 80-class/32-prototype decoder, confidence 0.25 and NMS IoU 0.7. The pinned weights are unchanged and no model was trained. Class-aware NMS replaces class-agnostic suppression. Candidate matching accepts a small object within a loose hint or under a click. Focused and wider-context crops address full-frame misses and a lid-only detection found in the left-to-right recording. Full-frame mask coordinates, not model class labels, flow into tracking. A configured model failing to load fails the production regression rather than silently skipping it.

Tracking retains CSRT, one clip-local identity, appearance/area/displacement guards, bounded lost-frame handling and mask-based geometry refresh every 25 sampled frames. An experimental 10-frame cadence produced an intermittent placement rejection on a previously passing input; it was not retained. OpenCV initialization is seeded, and repeated synthetic tracking is tested for identical observations. GrabCut no longer manufactures the original hint when no foreground is acquired. Fallback and lost-track tests now use an actual foreground fixture rather than random noise; a separate unresolved-foreground regression checks honest rejection. No previous test was deleted.

The low-lift recording initially failed placement despite a visibly resting final object. Diagnostics showed support contact falling as the scene darkened. Frame-median LAB lightness normalization restores exposure-tolerant contact observations with unchanged separation, placement and physical success thresholds. It then completed, but the first extracted path retained only three points because lift confirmation arrived late. Retaining earlier object motion after a lift is confirmed preserves seven points and the earlier reversals. Pickup time remains a functional estimate; this is not measured human contact timing.

The first simplifier collapsed collinear return paths. Finite-segment distance with an iterative ordered split now preserves reversals, closed excursions and corners, bounded to 32 points at 8 mm simplification tolerance. Median filtering removes isolated tracking jumps; small jitter is rejected. No raw-frame waypoint stream is sent to Panda. Controller results measure actual object convergence at every transport target; JSON fields alone do not count as execution proof.

### Physical recording evidence

The operator renamed the source videos and supplied descriptive filenames. Names, including double `.mp4` extensions, are preserved. The two original demonstration blobs still match Git hashes `e8c91059df437e7c9ee6b4399b6791f8ebc28a27` and `37bd2b31f23c972eda889998e07c1bac969df9f4`; only their filenames changed. Old Build 01/02 filenames and run records remain historical evidence, not rewritten aliases.

All successful rows below used the actual CPU YOLO implementation, persistent tracking, inferred lift/placement, and actual Panda execution. They are physical recorded videos, not new camera sessions performed during this pass. Camera descriptions are qualitative visual inspection, not calibrated angle measurements. ROI values follow earlier operator hints for these same clips, with 0.3 m workspace span. `table` is selected explicitly for the forward-path files.

- `pop-can-pick-up-right-to-left-1.mp4`: supplied frontal view; `front`; run `7fcf8db5ea7046b799352fc383445c4e`; 329 observations, 3 points / 2 transport targets; completed, 2.66 mm placement error.
- `pop-can-pick-up-right-to-left-2.mp4.mp4`: supplied frontal view; `front`; run `0b73762c32fd450d998d48cab2b375bb`; 311 observations, 2 points / 1 target; completed, 2.20 mm placement error.
- `pop-can-pick-up-left-to-right-1.mp4.mp4`: elevated oblique desk view; `front`; run `6dab0f714bd54ce688f246014896d7be`; 193 observations, 3 points / 2 targets; completed, 2.72 mm placement error. Initial lid-only acquisition was corrected by the wider crop.
- `pop-can-pick-up-forward-right-down-1.mp4.mp4`: elevated oblique desk view; `table`; run `68085c1582ba45c992538e767d4c9ce0`; 273 observations, 8 points / 7 targets; completed, 2.37 mm placement error; target errors 4.04-6.76 mm.
- `pop-can-pick-up-forward-right-back-forward-right-back-down-low-lift-1.mp4.mp4`: elevated desk view with exposure change; `table`; initial run `bc7ed5982b7d46f082ec27f3a47b02ae` failed placement. Exposure correction run `44fe4c0903154c07a78080f4d20467f9` completed but retained only the later 3-point tail. Pre-QA run `f7382f07b33b4d11af0d7c88883af060` retains 7 points / 6 targets from 296 observations, completed with 3.00 mm placement error and 1.92-5.89 mm target errors. Later source inspection found drifting geometry despite robot success; see the cumulative geometry QA below. All earlier outcomes remain recorded.
- `pop-can-pick-up-forward-right-back-down-up-down-1.mp4.mp4`: elevated desk view; `table`; run `61fffb3e952b4bea8b347787aec5ce2e` failed tracking. Diagnostic frames around observations 117-122 show the object partly cut off at the left edge. FAILED REAL-WORLD TEST; no robot execution or placement result. Do not count it as a supported-view success.

Five labeled recordings completed across this closure pass. That is not five newly operated live sessions or proof of all requested path/view categories. A distinct physical return-near-origin demonstration, calibrated viewpoint-envelope coverage and the failed frame-exit case remain open.

### Regression Matrix

Each row records Previous State; Current State; Automated Test; Synthetic Validation; Real Video Validation; Panda E2E; Remaining Limitation. Status labels distinguish evidence types rather than treating implementation as completion.

- Live camera: previous synthetic capture verified; current VERIFIED - SYNTHETIC; automated `camera.spec.ts`; synthetic actual recording/save/pipeline; real saved operator clips above; Panda synthetic capture and recorded clips; physical permissions/new live operation not performed here.
- Uploaded video: previous supplied-video E2E; current VERIFIED - PANDA E2E; automated `test_pipeline.py`; synthetic uploaded return video; real renamed originals; Panda completed; controlled single-episode scope.
- Rough object selection: previous injected mask/GrabCut; current VERIFIED - REAL VIDEO; automated `test_object_segmentation.py`; loose-box/click matching; real production target acquisition; Panda successful rows above; extremely loose/ambiguous hints can still fail.
- YOLO segmentation: previous loaded but fallback on can clips; current VERIFIED - REAL VIDEO; automated mandatory production-model test in image; synthetic decoder/crop tests; real supplied and labeled clips; Panda successful rows used YOLO; no general vocabulary or GPU proof.
- GrabCut fallback: previous useful but could return hint; current VERIFIED - AUTOMATED; automated explicit fallback and empty-foreground cases; synthetic support scenes; real initial fallback history preserved; Panda previous Build 02 fallback runs; cannot resolve every foreground and now fails honestly.
- Object mask: previous initial-only mask; current VERIFIED - REAL VIDEO; automated crop/letterbox/bounds cases; synthetic mask acquisition; real sensible acquired bounds; Panda normalizes geometry into skill; dense mask propagation/shape reconstruction not claimed.
- Object tracking: previous CSRT without refresh; current VERIFIED - REAL VIDEO; automated identity/refresh/lost-track tests; synthetic six viewpoints; real five successes and one loss; Panda successful rows; occlusion/frame exit remains bounded failure.
- Persistent identity: previous clip-local ID; current VERIFIED - AUTOMATED; automated mask refresh and matching tests; synthetic stable ID; real tracked clips; Panda consumes normalized motion; similar overlapping distractors remain a limitation, not cross-clip identity.
- Support surface: previous colour/rest-pose evidence; current VERIFIED - REAL VIDEO; automated exposure/contact and surface tests; synthetic table scenes; real low-lift exposure failure corrected; Panda low-lift run completed; monocular colour evidence is not measured contact/depth.
- Vertical lift: previous synthetic and real acceptance; current VERIFIED - PANDA E2E; automated viewpoint/lift cases; synthetic six views; real supplied clips; Panda physical lift measured; camera envelope not physically calibrated.
- Slanted lift: previous synthetic only; current PARTIAL; automated slanted fixture; synthetic passed; real projected forward-path clips evaluated; Panda safe-clearance path completed; no metric physical slant reconstruction or separately calibrated slanted capture.
- Sliding rejection: previous synthetic rejection; current VERIFIED - SYNTHETIC; automated slide/no-separation cases; synthetic front/elevated slides; real labeled slide-only input unavailable; Panda not started for rejected inputs; add physical slide-only evidence before freeze.
- Placement: previous stable return gate; current VERIFIED - REAL VIDEO; automated stability/exposure cases; synthetic returns/noise; real exposure correction; Panda measured release/final errors; insufficient rest/hidden contact still rejects.
- Straight trajectory: previous one goal; current VERIFIED - PANDA E2E; automated simplifier/physics/pipeline cases; synthetic straight; real lateral clips; Panda completed; projected mapping only.
- Forward/backward trajectory: previous X unsupported; current VERIFIED - PANDA E2E; automated explicit-table mapping/physics; synthetic reversal; real low-lift projected reversals; Panda five ordered targets on the geometry-QA rerun; not recovered depth and mode is not automatic.
- L-shaped trajectory: previous single target; current PARTIAL; automated simplifier/physics; synthetic corner survives; real forward-right clip gives multi-axis path; Panda six targets on the geometry-QA rerun; a separately labelled physical L-shape ground truth remains open.
- Multi-turn trajectory: previous start/end collapse; current VERIFIED - PANDA E2E; automated ordered-corner/physics and delayed-lift regression; synthetic multi-turn; real low-lift six-point geometry-QA result; Panda each point measured; frame-exit multi-turn clip still fails.
- Return-near-origin trajectory: previous rejected small net motion; current VERIFIED - SYNTHETIC; automated `test_recorded_return_path_reaches_panda_in_order`; synthetic recorded out-and-back; real dedicated clip unavailable; Panda actual excursion/return measured; physical return-near-origin gate remains open.
- Skill extraction: previous start/goal only; current VERIFIED - PANDA E2E; automated timing/path/schema cases; synthetic jitter/corners/returns; real ordered points; Panda consumes them; inferred pickup timing and projection remain approximate.
- Robot mapping: previous one transport goal; current VERIFIED - AUTOMATED; automated old/new skill and bounds tests; synthetic two-axis fixtures; real generated skills accepted; Panda actual ordered targets; deploy updated validators with new producers.
- Panda waypoint execution: previous one target; current VERIFIED - PANDA E2E; automated five physical path fixtures; synthetic fixture paths; real multi-target runs; measured object convergence, not just commands; fixed target asset and existing workspace/deadline limits.
- Overall E2E: previous controlled baseline; current PARTIAL Tier 1 closure; automated root/browser/service suites; synthetic saved/uploaded return and camera workflows; real five successes/one failure; Panda outcomes above; physical coverage and hosted final CI still required.

### Open Acceptance Gates

- [x] Production CPU segmentation works on representative real frames; no mocked-only claim.
- [x] Loose hints acquire actual geometry; no unresolved hint promoted to a mask.
- [x] Ordered corners/reversals/excursions reach Panda and are checked against measured object positions.
- [x] Five existing labeled physical recordings evaluated successfully, with failed attempts retained.
- [ ] Physical slide-only, calibrated camera-envelope, distinct L-shaped and return-near-origin acceptance completed.
- [ ] Failed frame-exit demonstration resolved or replaced with an in-envelope capture and verified.
- [ ] New physical live sessions verified with operator/device permissions.
- [ ] Final pushed implementation has a green hosted workflow; local checks are not a hosted result.
- [ ] Freeze Tier 1 only when all applicable acceptance gates pass.

### Local Verification Before Geometry QA

Completed on 2026-10-11, local time:

- Perception image: 42 passed, including actual CPU weights, crop/mask/NMS matching, unresolved foreground, refresh/identity, repeated tracking, exposure, delayed lift and ordered trajectory cases. Host run: 41 passed, 1 skipped because weights are image-local. No configured-production-model skip is accepted.
- Orchestrator image: 9 passed. Simulation image: 17 passed, including old skills and five actual straight/reversal/L/multi-turn/return-path physics executions. Upstream library deprecation warnings remain non-fatal.
- Final root suite: `RUN_INTEGRATION=1 python -m pytest tests -q`, 10 passed in 102.06 seconds. Earlier full runs included a Docker stop command exceeding 40 seconds; the recovery block now includes stop and the bounded CLI allowance is 120 seconds. The two outage cases passed on focused rerun before the final complete green run. Robot execution deadlines and physical tolerances were not relaxed.
- Final browser suite: 10 passed in 1.5 minutes; 2 duplicate mobile physics executions intentionally skipped. Actual synthetic-camera recording/save/physics, supplied-video physics, inline provenance, time-aligned moving object bounds, source/robot playback pixels, mobile layout and failure paths passed. Desktop/mobile screenshots were inspected. No physical device was accessed by automated tests.
- Synthetic uploaded return-path tests use the supplied texture, not a newly collected physical demo. Generated UUID videos remain ignored. Measured outbound motion is over 5 cm and every retained target is verified before return/release; net displacement alone is not used as success evidence.
- Four production images built and a clean project-scoped startup completed with all four services healthy. Two earlier cold starts overlapped separate physics checks and exceeded the original health grace; simulation now has 120 seconds of startup grace within the unchanged 240-second lifecycle wait. The final perception changes also rebuilt and started successfully in isolation.
- Ruff lint/format, Prettier, TypeScript/production web build, Bash syntax, Compose configuration, all eight documents' local links and Git whitespace checks passed. CI now runs all three service suites, including mandatory production segmentation and actual waypoint physics, before root/browser verification.
- Git dry-run includes intended source/config/docs and the operator-renamed/added demonstration files. Original video blob hashes are unchanged. Local environments, model/runtime output, UUID uploads, camera recordings, diagnostics, screenshots and traces remain ignored. No staging, commit, push, history rewrite or external deployment was performed. SSH remote read access works; hosted verification of these changes still requires an authorized commit/push.

Local checks are not a hosted Actions result. Keep the unsupported frame-exit clip, unmeasured physical camera envelope, physical slide-only/return-near-origin coverage and new live-operation gates open. These are limitations of the acceptance record, not reasons to erase passing regression evidence. Stop scope expansion at Tier 1; no hand tracking, training, full reconstruction, obstacle planner or additional service was added.

### Geometry QA (2026-10-12)

Successful Panda placement alone did not establish source-trajectory fidelity. The earlier low-lift source overlay included a large background rectangle around 5.2 seconds. That screenshot remains as `data/runs/acquired-geometry-before-qa.png`, ignored by Git. Source geometry and execution must both be inspected; the earlier successes above are historical controller evidence, not blanket proof of correct tracking.

Findings and retained corrections:

- Negative-origin clipping previously kept the original width/height instead of the visible intersection. Correct bounds before using them for contact, tracking or visualization. Initial and refreshed masks now use the same four-pixel padding and intersection clipping.
- Near-neutral hue is unstable, and hue/saturation alone cannot distinguish a silver object from dark neutral support. Tracking uses a normalized HSV histogram, suppresses neutral-pixel hue, and normalizes brightness against the full-frame 99th percentile. The rotated target measured 0.664 Bhattacharyya distance from its initial appearance; inspected unrelated candidates measured 0.799-0.893. The 0.75 appearance limit is still combined with overlap, scale and shape guards, not treated as recognition proof.
- Foreground features come only from the acquired mask. OpenCV forward/backward optical flow, checked to two pixels, and a RANSAC partial-affine transform follow their motion and scale. At least six consistent points are required. A failed estimate falls back to CSRT; it does not promote the operator hint to object geometry. Periodic segmentation resets the features. Normal cadence is 25 frames; when foreground features are unavailable, retry every five frames, or immediately when CSRT fails.
- Larger YOLOv8s-seg weights were evaluated but not retained. One difficult frame improved confidence (0.767 versus 0.294), yet the mandatory original-video acquisition regression fell back to GrabCut and failed. The final runtime retains the original checked YOLOv8n-seg weights; no training, new dependency, service or repository model cache was added.
- Intermediate low-lift runs `cdc6d46ef33e43678684500d0c0465bc`, `ff45a3646e724b2fbb04285a96de6d73`, `bbb991d042224b509650eee699743d54` and `ca715dc2d4a34bb69e368986aae932b2` completed robot execution but still had incorrect source bounds. Clipping-only run `b8fd62520f6e4db0a6395fc6063f2ad3` failed placement. These are diagnostic attempts, not additional accepted demonstrations.
- Adaptive foreground refresh run `a0081f42eab84f4b8742d202be6e79ca` completed with 296 observations, six points / five targets, 2.87 mm placement error and 5.45-8.04 mm target errors. At 5.2 seconds, tracked center U was 0.32585 versus an independently inspected production mask center near 0.3273 (within one pixel at tracking resolution). This demonstrates correction at the inspected frame, not dense-mask ground truth for the entire clip.
- The subsequent complete root suite caught a previous-demo regression: run `6db1b35913c94daca87d4bf257307102` selected a much wider similarly colored foreground and then failed insufficient transport. Root result: nine passed, one failed. Reacquisition now also bounds aspect-ratio change to half/twice the acquired padded shape. This guard is object-relative, not a can/class filter. Extreme pose changes and indistinguishable overlapping objects remain unsupported uncertainty.

Added regressions cover visible intersection clipping, legitimate mask scale changes, neutral object/support discrimination under exposure gain, foreground-flow correction of a drifting rectangular tracker, and rejection of wider same-color distractors. No earlier regression was removed. Host perception: 47 passed, one skipped for image-local weights. Final image, recorded-video, root and browser verification follows below; Tier 1 remains unfrozen.

### Recorded-Video Replay Before Category QA

All six operator-named files were replayed sequentially after the shape guard, with the same explicit hints, spans and qualitative camera descriptions recorded above. These are existing physical recordings, not newly operated live sessions. All five successes initialized with production CPU YOLO, retained one clip-local identity, passed sustained lift and stable-placement extraction, and verified actual Panda grasp/lift/release and every emitted transport target. No automatic execution retry or physical tolerance relaxation was used.

- Right-to-left 1: `cb7cbf72737d4807ae155c99ea342897`; 329 observations; two points / one target; completed; 2.20 mm placement error, 6.48 mm waypoint error.
- Right-to-left 2: `cf74a9bb1d23498fb3358e222e0072fe`; 311 observations; two points / one target; completed; 2.20 mm placement error, 6.04 mm waypoint error.
- Left-to-right 1: `aed164739f19424fa1f6753350a6e623`; 193 observations; three points / two targets; completed; 2.70 mm placement error, 3.09-10.10 mm waypoint errors.
- Forward-right-down 1: `73bd19ecb0a84b3a93916dfade5fc20b`; 273 observations; seven points / six targets; completed; 2.27 mm placement error, 3.48-7.79 mm waypoint errors.
- Forward-right-back-forward-right-back-down-low-lift 1: `d00f6395712b47ffb0476dc9af5b397a`; 296 observations; six points / five targets; completed; 2.87 mm placement error, 5.45-8.04 mm waypoint errors. Its geometry and execution match the earlier adaptive-refresh result at the inspected low-lift frame.
- Forward-right-back-down-up-down 1: `e2348e3ecabe406e8b812ebcb6e47ccd`; FAILED REAL-WORLD TEST - lost tracking. No skill, lift/placement acceptance, waypoint count, Panda execution or placement error is available for this failed run. The previously inspected frame-exit limitation remains open.

Five completions do not establish all five representative physical path categories. The dedicated physical return-near-origin, slide-only, calibrated-view and new live-operation gates remain open. Unit matching verifies click hints; production physical click-only acquisition has not been separately verified. The bounded identity heuristic does not guarantee arbitrary occlusion, shape/rotation or distractor handling.

### Category QA

The next source-video screenshot revealed that the original lateral demo could still switch onto the demonstrator at seven seconds, despite completing placement. Preserve `data/runs/original-geometry-before-category-qa.png` as diagnostic evidence. The shape guard alone was insufficient. The ten-test root suite passed in 143.59 seconds before it checked this specific source boundary; that green result did not prove source fidelity.

Inspection found that the target's detector category differed from the selected person. Semantic predictions for the target also changed across its poses. A strict category guard was evaluated entirely inside perception. It fixed the lateral snapshot but prevented valid geometry refresh in another recording. It was not retained. A rejected refresh no longer computes an unused GrabCut mask; GrabCut acquisition remains tested.

The existing complete-pipeline test now checks the actual source observation at seven seconds against the held object's location and size, not just final placement. The existing browser execution checks the corresponding overlay position. No test was removed or extra framework added. A diagnostic production tracking pass kept center U at 0.136 and tight bounds at seven seconds, instead of the earlier person rectangle near U 0.417.

Strict detector-category replay results remain diagnostic evidence: lateral runs `5f839baae61c4944b2b4bca7c2c5788e` and `723708550254400b942a7adcba0ad607` completed with three points each; left-to-right `8afb1a1cb3054e3f98a5cfddd77b9b5d` completed with two points; low-lift `2ba649c1210c40488db08fe8844a331f` completed with six points. Forward-right-down `7bb2d9c2a4de498297bb5155be96f469` failed tracking, and frame-exit `ee146157d2dd4ff4a500ed5e2a15ae87` still failed. Strict category locking was not retained because changing predictions for the same object prevented a valid geometry refresh.

Coarse person/object grouping was also evaluated and not retained. Lateral run `f1d7c6bf543b48d599dc09aa5dadb19c` completed placement but still had the wrong source bounds at seven seconds. Other diagnostic completions were `58bd6097774143f6b9b75147a3932c51`, `eb481734f565417c984a52594b524f50`, `7b184372cc4e4cce8a9f121846aad828` and `3c35ef0bac874056be9f4d254868679d`; frame-exit `2d981d84aa0b4cf8b10ab64f1d4a9d3f` failed. Semantic predictions were not a reliable identity boundary for these clips; none of this classification plumbing remains in tracking or public output.

The retained correction anchors refresh area to the last successfully acquired mask. A drifting rectangular tracker must not progressively enlarge the admissible object. A fully visible previous mask allows at most twice its area; an edge-clipped mask allows up to four times as the same object re-enters. Existing initial/predicted area, overlap, appearance and aspect-ratio bounds remain. This is geometry-relative, independent of detector vocabulary, and preserves the known clipped low-lift recovery. The existing distractor regression now checks a larger same-color, same-shape candidate, rather than relying only on shape rejection. Final complete replays and verification follow below.

### Reacquisition Boundary Closure

Area anchoring alone still admitted a smaller background candidate. Runs `d7fd96f24add41f5b395019088b315b2` and `d694ba11827345ac841d6839d7a70e19` failed stable placement; their full root suites each had nine passes and one failure (117.53 and 114.44 seconds). Do not interpret those failures as a reason to relax support or placement checks.

The exact 6.4-second decision had predicted bounds `[190, 13, 138, 212]` and candidate bounds `[281, 0, 128, 258]`. Intersection divided by the smaller box area gave 0.34 and admitted an edge overlap. Intersection-over-union is about 0.19 and rejects it at the unchanged 0.25 threshold. The larger alternative candidate exceeded twice the last mask's 24,000-pixel area and is rejected by the mask anchor. Both boundaries are needed; no semantic class lock is retained.

Focused-crop selection also rejects a mask cut by an internal crop boundary, then tries wider context. Actual frame-edge clipping remains allowed. The existing crop-coordinate regression exercises this retry, and the periodic-refresh regression now includes a higher-confidence, same-color candidate that only overlaps the track's edge. The first augmented distractor fixture moved into substantial target overlap and was ambiguous; the corrected fixture keeps the intended edge-overlap boundary distinct. No baseline regression or acceptance assertion was deleted.

Focused original-video E2E `4d26c4ffb84c421da8d217de70b644c5` passed in 46.61 seconds, including actual YOLO, held-object position/size at seven seconds, skill and Panda execution. The regenerated `original-geometry-after-qa.png` visibly follows the held object; the earlier wrong overlay remains separately preserved. This inspected boundary is stronger evidence than placement alone, not dense per-frame ground truth. All relevant complete suites and named inputs still require the final rerun below.

### Final Geometry-Checked Recorded Replay

The final model-independent mask-area, IoU and crop-boundary implementation replayed all six named recordings sequentially. Calibration hints, 0.3 m span and qualitative view descriptions are unchanged from the physical evidence above. Every successful row acquired with actual CPU YOLO, retained clip-local ID 1, passed lift/stable-placement extraction and verified actual simulated grasp/lift/release plus each ordered target. These are existing physical recordings, not new live-camera sessions.

- Right-to-left 1: `741765026cf4472a863fe4a79f2cf58e`; 329 observations; three points / two targets; completed; 2.70 mm placement error, 4.82-6.08 mm waypoint errors. At seven seconds, U is 0.117 and the bounds contain the held object, not the torso. The overshoot and short return survive.
- Right-to-left 2: `65dd536912e746df8e126f674b313b27`; 311 observations; two points / one target; completed; 2.20 mm placement error, 6.07 mm waypoint error.
- Left-to-right 1: `07d396984f534c9aac1f334dbe7be181`; 193 observations; three points / two targets; completed; 2.70 mm placement error, 3.12-10.08 mm waypoint errors.
- Forward-right-down 1: `774bf8e9b14648eb812c38d5b314b2f2`; 273 observations; seven points / six targets; completed; 2.27 mm placement error, 3.48-7.79 mm waypoint errors.
- Forward-right-back-forward-right-back-down-low-lift 1: `fb7afc2f375f48dfa1d13a95d3a325d7`; 296 observations; six points / five targets; completed; 2.87 mm placement error, 5.45-8.04 mm waypoint errors. U at 5.2 seconds is 0.32585; the later clipped-object recovery retains the remaining turns.
- Forward-right-back-down-up-down 1: `8e6d36c6bf1f4d05a6d7e6f53d53f627`; FAILED REAL-WORLD TEST - lost tracking; no accepted lift/placement, skill, waypoints, robot execution or placement error. Initial-frame diagnostics acquired a YOLO mask, but that does not establish full-clip tracking. Frame exit remains unsupported.

Source and robot playback were decoded and inspected in paired screenshots for all five completions: `original-geometry-after-qa.png`, `geometry-right-left-2.png`, `geometry-left-right.png`, `geometry-forward-right.png`, `acquired-geometry-after-qa.png` and the additional `geometry-low-lift-return.png`. These local diagnostics stay ignored by Git. Bounds follow the intended object at the inspected frames; hand occlusion, edge clipping and rapid motion can still yield partial geometry. This is visual spot-check evidence, not pixel-level ground truth throughout each clip or recovered metric 3D.

### Final Verification (2026-10-12)

- Perception image: 48 passed in 28.27 seconds, including mandatory actual weights and the retained crop, mask, foreground flow, identity, support and trajectory regressions. Host tracking subset: 11 passed; the earlier whole-host run had 47 passes and one image-local-weight skip.
- Orchestrator image: 9 passed in 5.60 seconds. Simulation image: 17 passed in 84.78 seconds, including legacy skill execution and all five ordered-path physics cases. Upstream deprecation warnings remain non-fatal.
- Complete final root suite: 10 passed in 111.93 seconds. This includes the strengthened original-video source-identity assertion, actual Panda output, synthetic uploaded return-path excursion/ordered convergence, honest invalid/failed manipulation, lifecycle, dependency outages and recovery.
- All four images rebuilt and a project-scoped clean startup passed with all services healthy. The final stylesheet organization and native-select accessibility changes also rebuilt and started successfully in the web service. No physical execution was in progress during lifecycle checks.
- Final browser suite: 10 passed in 1.8 minutes, two duplicate mobile physics cases intentionally skipped. Actual synthetic-camera recording/save/physics, supplied-video physics, source-overlay position, inline provenance/observations, source/robot playback pixels, responsive layout, permissions/discard and readable failure states passed on the rebuilt app. No physical camera or microphone was accessed.
- Ruff lint/format, Prettier, production TypeScript/Vite build, Compose configuration, Bash syntax, all eight documents' local links and Git whitespace checks passed. CI retains pinned actions, bounded execution, failure diagnostics and all service/root/browser suites. The equivalent local checks are green; no hosted result is claimed.
- Final Git dry-run contains intended source/config/docs plus the operator-renamed and added named recordings. The two original video blobs are unchanged. Environments, dependencies, models, build output, UUID uploads, camera captures, screenshots, diagnostics and generated runs remain ignored. No staging, commit, push, branch creation or history rewrite was performed. SSH remote read access was verified; push permissions and hosted CI are not verified by that read.

The compact workspace rules now match the implementation: 4-8px corners, restrained headings, unframed page sections and no nested cards. Style definitions sit with their owning controls/media rather than before the shared tokens. No new architecture, service, model class interface, training dependency, hand tracker, document or Build 03 was introduced.

Tier 1 remains unfrozen. Five successful source-to-simulation recordings do not supply distinct physical return-near-origin/slide-only/L-shaped ground truth, calibrated viewpoint coverage or new device-operated live sessions. Hosted workflow verification remains separate and pending an authorized commit/push.

### Hosted Formatting Failure Follow-Up

The operator supplied a hosted failure at `ruff format --check`: seven perception files required formatting, while lint passed. A clean archive of committed `018253c` reproduced exactly those seven files with the pinned Ruff 0.11.13. The current working tree passed all 27 files before this follow-up; the uncommitted formatting changes were not present in the revision checked by CI. This is a reproduced committed-source formatting failure, not a green hosted result.

The local global Ruff command resolves to version 0.16.5, while the project environment and `requirements-dev.txt` use 0.11.13. `pyproject.toml` now requires the pinned version, and the workflow prints it and invokes checks through `python -m ruff` using the same Python that installed the development requirements. Keep the format check blocking; do not hide it or automatically rewrite source in CI. Development instructions now use these same commands. Commit the formatted source together with the pipeline/configuration changes before rerunning hosted verification. No commit or push was performed during this follow-up.

Follow-up verification: pinned Ruff lint and format checks passed all 27 files locally and in a fresh Python 3.11 Linux container with the workspace mounted read-only. The incompatible global Ruff failed explicitly at the version guard, as intended. Prettier, TypeScript/Vite build, Compose configuration and all four image builds passed. These changes affect checker configuration and documentation only; the previously recorded application test results are not claimed as rerun here. The temporary committed-source archive remains ignored under `data/runs/ci-head-check`; the attempted cleanup was denied by the command policy. Hosted verification of the corrected working tree remains pending its commit/push.
