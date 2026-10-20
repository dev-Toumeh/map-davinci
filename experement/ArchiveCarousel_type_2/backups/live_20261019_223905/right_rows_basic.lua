return bmd.readstring([====[
{
 Tools = ordered() {
		Media_file4 = Loader {
			CustomData = {
				MediaProps = {
					MEDIA_FORMAT_TYPE = "JPEG",
					MEDIA_HEIGHT = 1503,
					MEDIA_ID = "6c9d219b-1394-4918-a2d5-fb65711b2bc3",
					MEDIA_IS_SOURCE_RES = true,
					MEDIA_LAYER_DESC = {
					},
					MEDIA_MARK_IN = 0,
					MEDIA_MARK_OUT = 0,
					MEDIA_NAME = "image4",
					MEDIA_NUM_FRAMES = 1,
					MEDIA_NUM_LAYERS = 0,
					MEDIA_PAR = 1,
					MEDIA_PATH = "/Users/naseemtoumeh/edit-projects/project2/Aj+/images/m0OR9wr-Ou9_OgKmrZcSZMY119D-_g3VfyjWqvUsYtH6eIbWq8nIgAFAvqMsmdu_3t0ou1O_RaDlDaFXd2795UHdtygO087btZG24l73qcZN60QFSiVgSZ-RunB1d6e0SXgsF8dQNHG_CtjyKFL-2CzSspTtVV6IP7NFMgSm2TvnqQZC4-mP__cOr71ACSmF.jpeg",
					MEDIA_SRC_FRAME_RATE = 24,
					MEDIA_START_FRAME = 0,
					MEDIA_WIDTH = 2000,
					__Queried = true
				},
				MEDIA_ID = "6c9d219b-1394-4918-a2d5-fb65711b2bc3",
			},
			Inputs = {
				GlobalOut = Input { Value = 837, },
				MediaSource = Input { Value = FuID { "MediaPool" }, },
				MediaID = Input { Value = "6c9d219b-1394-4918-a2d5-fb65711b2bc3", },
				AudioTrack = Input { Value = FuID { "Timeline Audio" }, },
				Layer = Input { Value = "", },
				ClipTimeEnd = Input { Value = 0, },
				Loop = Input { Value = 1, },
				["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },
				DeepOutputMode = Input {
					Value = 0,
					Disabled = true,
				},
				LeftAudio = Input {
					SourceOp = "Left",
					Source = "Data",
				},
				RightAudio = Input {
					SourceOp = "Right",
					Source = "Data",
				},
			},
			ViewInfo = OperatorInfo { Pos = { 1375, 16.197 } },
			Version = 1,
			Clips = {
				Clip {
					ID = "Clip1",
					Multiframe = true,
					Filename = "/Users/naseemtoumeh/edit-projects/project2/Aj+/images/m0OR9wr-Ou9_OgKmrZcSZMY119D-_g3VfyjWqvUsYtH6eIbWq8nIgAFAvqMsmdu_3t0ou1O_RaDlDaFXd2795UHdtygO087btZG24l73qcZN60QFSiVgSZ-RunB1d6e0SXgsF8dQNHG_CtjyKFL-2CzSspTtVV6IP7NFMgSm2TvnqQZC4-mP__cOr71ACSmF.jpeg",
					Length = 1,
					LengthSetManually = true,
					GlobalEnd = 837,
					TrimOut = 0,
					Loop = 0
				}
			}
		},

		object_2_right = MultiMerge {
			NameSet = true,
			Inputs = {
				LayerOrder = Input { Value = ScriptVal { { [0] = 1, 2 } }, },
				Background = Input {
					SourceOp = "Right_Stack2_Background",
					Source = "Output",
				},
				["Layer1.Foreground"] = Input {
					SourceOp = "Media_file4_Frame",
					Source = "Output",
				},
				LayerName1 = Input { Value = "t1 Layer", },
				["Layer2.Foreground"] = Input {
					SourceOp = "Right_Stack2_Vintage8mm",
					Source = "Output",
				},
				["Layer2.Size"] = Input { Value = 0.63, },
				["Layer2.Blend"] = Input { Value = 0.37, },
				LayerName2 = Input { Value = "MediaIn1: Vintage 8mm Film.png Layer", }
			},
			ViewInfo = OperatorInfo { Pos = { 1045, 16.197 } },
		},
		Right_Stack2_Background = Background {
			Inputs = {
				GlobalOut = Input { Value = 837, },
				Width = Input { Value = 3840, },
				Height = Input { Value = 2160, },
				UseFrameFormatSettings = Input { Value = 1, },
				["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },
				TopLeftAlpha = Input { Value = 0, }
			},
			ViewInfo = OperatorInfo { Pos = { 751.256, -16.4251 } },
		},
		Right_Stack1_Vintage8mm = Loader {
			CustomData = { MEDIA_ID = "85583b41-424d-4433-9be0-3060e9420f5d", MediaProps = { __Queried = true, MEDIA_NUM_LAYERS = 0, MEDIA_FORMAT_TYPE = "PNG", MEDIA_PATH = "/Users/naseemtoumeh/edit-projects/general/VFX assets/frames/Vintage 8mm Film.png", MEDIA_START_FRAME = 0, MEDIA_LAYER_DESC = {
					}, MEDIA_NAME = "Vintage 8mm Film.png", MEDIA_HEIGHT = 1086, MEDIA_SRC_FRAME_RATE = 24, MEDIA_IS_SOURCE_RES = true, MEDIA_ID = "85583b41-424d-4433-9be0-3060e9420f5d", MEDIA_MARK_OUT = 0, MEDIA_WIDTH = 1448, MEDIA_NUM_FRAMES = 1, MEDIA_MARK_IN = 0, MEDIA_PAR = 1 }, },
			Inputs = {
				GlobalOut = Input { Value = 837, },
				MediaSource = Input { Value = FuID { "MediaPool" }, },
				MediaID = Input { Value = "85583b41-424d-4433-9be0-3060e9420f5d", },
				AudioTrack = Input { Value = FuID { "Timeline Audio" }, },
				Layer = Input { Value = "", },
				ClipTimeEnd = Input { Value = 0, },
				Loop = Input { Value = 1, },
				["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },
				DeepOutputMode = Input {
					Value = 0,
					Disabled = true,
				},
				LeftAudio = Input {
					SourceOp = "Left",
					Source = "Data",
				},
				RightAudio = Input {
					SourceOp = "Right",
					Source = "Data",
				},
			},
			ViewInfo = OperatorInfo { Pos = { 1726.49, 78.1753 } },
			Version = 1,
			Clips = {
				Clip {
					ID = "Clip1",
					Multiframe = true,
					Filename = "/Users/naseemtoumeh/edit-projects/general/VFX assets/frames/Vintage 8mm Film.png",
					Length = 1,
					LengthSetManually = true,
					GlobalEnd = 837,
					TrimOut = 0,
					Loop = 0
				}
			}
		},
		Right_Stack2_Vintage8mm = Loader {
			CustomData = { MEDIA_ID = "85583b41-424d-4433-9be0-3060e9420f5d", MediaProps = { __Queried = true, MEDIA_NUM_LAYERS = 0, MEDIA_FORMAT_TYPE = "PNG", MEDIA_PATH = "/Users/naseemtoumeh/edit-projects/general/VFX assets/frames/Vintage 8mm Film.png", MEDIA_START_FRAME = 0, MEDIA_LAYER_DESC = {
					}, MEDIA_NAME = "Vintage 8mm Film.png", MEDIA_HEIGHT = 1086, MEDIA_SRC_FRAME_RATE = 24, MEDIA_IS_SOURCE_RES = true, MEDIA_ID = "85583b41-424d-4433-9be0-3060e9420f5d", MEDIA_MARK_OUT = 0, MEDIA_WIDTH = 1448, MEDIA_NUM_FRAMES = 1, MEDIA_MARK_IN = 0, MEDIA_PAR = 1 }, },
			Inputs = {
				GlobalOut = Input { Value = 837, },
				MediaSource = Input { Value = FuID { "MediaPool" }, },
				MediaID = Input { Value = "85583b41-424d-4433-9be0-3060e9420f5d", },
				AudioTrack = Input { Value = FuID { "Timeline Audio" }, },
				Layer = Input { Value = "", },
				ClipTimeEnd = Input { Value = 0, },
				Loop = Input { Value = 1, },
				["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },
				DeepOutputMode = Input {
					Value = 0,
					Disabled = true,
				},
				LeftAudio = Input {
					SourceOp = "Left",
					Source = "Data",
				},
				RightAudio = Input {
					SourceOp = "Right",
					Source = "Data",
				},
			},
			ViewInfo = OperatorInfo { Pos = { 1726.49, 78.1753 } },
			Version = 1,
			Clips = {
				Clip {
					ID = "Clip1",
					Multiframe = true,
					Filename = "/Users/naseemtoumeh/edit-projects/general/VFX assets/frames/Vintage 8mm Film.png",
					Length = 1,
					LengthSetManually = true,
					GlobalEnd = 837,
					TrimOut = 0,
					Loop = 0
				}
			}
		},
 Right_Stack2_Fit = BetterResize { Inputs = {
 Input = Input { SourceOp = "Media_file4", Source = "Output", },
 Width = Input { Value = 328, }, Height = Input { Value = 246, },
 }, },
 Right_Stack2_CardCanvas = Crop { Inputs = {
 Input = Input { SourceOp = "Right_Stack2_Fit", Source = "Output", },
 XSize = Input { Value = 328, }, YSize = Input { Value = 480, },
 KeepCentered = Input { Value = 1, }, },
 },
 },
}
]====])
