SWIPE UP LOOP — Fusion group

Contains all 12 RGBA PNG frames from your GIF (480 x 480).
Original timing: 70/60/70/70/60/70/70/60/70/70/60/60 ms; loop = 0.79 seconds.

QUICK INSTALL ON MAC
For this workspace, drag SwipeUpLoop.setting directly into Fusion. Its PNG
path is already set to skills/my-fusion-skills/assets/gif_to_png_loop/Frames.
Use a fresh group instance after updating the setting. Set Timeline FPS to
match your composition, then play: the timing expression repeats every
0.79 source seconds, and the Loader range is extended to frame 1000000.

INSTALL AFTER MOVING THE PACKAGE TO ANOTHER FOLDER
1. Extract this ZIP into a permanent folder. Keep the Frames folder there.
2. Open your composition on the Fusion page.
3. Open Workspace > Console and choose Lua.
4. Run the following, replacing the path with your extracted folder:
   dofile("/Users/YOUR_NAME/Downloads/SwipeUpLoop/Install_SwipeUpLoop.lua")
5. Choose Frames/swipe_0000.png in the dialog and confirm your timeline FPS.
6. Connect SwipeUpLoop to the foreground input of your 2D Merge, or to an
   ImagePlane3D for use in your 3D scene.

CONTROLS
Speed: 1 = original timing, 2 = twice as fast, 0.5 = half speed, 0 = pause.
Timeline FPS: match your timeline (24, 25, 30, 60, 29.97, etc.).
Offset: change the starting phase, in seconds of the source animation.
The loop starts at the composition render start and repeats for the full comp.

MANUAL INSTALL
Drag SwipeUpLoop.setting into the Fusion node editor (or copy its full text
and paste into the node editor). Open the group, select PNGFrames, and browse
to Frames/swipe_0000.png. Ensure it loads the sequence of 12 frames rather than
a single image, Trim In = 0, Trim Out = 11, Global In = 0, Loop enabled,
and Global Out extending through your composition. Set Timeline FPS on
the group. The automatic installer handles paths for you.

KEEP THE ASSETS
The group references PNG files on disk; it does not embed the pixels in the
.setting file. If you move the Frames folder, relink PNGFrames inside the group.

VALIDATION
All frames and timing were checked against the source GIF. Settings and the
installer were checked for Lua syntax. Resolve/Fusion is not available here,
so actual import and playback still need verification in your installation.
