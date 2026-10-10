"""Cross-subject data fixtures, not a production topic/template router."""


def counting_scenes():
    objects = [{"id":f"b{i}", "kind":"circle", "at":[x,0], "size":[.7,.7],
                "fill":.9, "color":"#38BDF8" if i < 3 else "#FBBF24"}
               for i, x in enumerate([-4,-3,-2,2,3])]
    objects += [{"id":"sum", "kind":"text", "text":"3 + 2 = 5", "at":[0,-1.9], "size":[4,.7], "visible":False},
                {"id":"difference", "kind":"text", "text":"5 − 2 = 3", "at":[0,1.8], "size":[4,.7], "visible":False}]
    return [{"type":"scene", "heading":"把两组珠子合在一起", "caption":"看物体怎样移动，不只读算式", "objects":objects,
             "groups":[{"id":"blue", "members":["b0","b1","b2"]}, {"id":"yellow", "members":["b3","b4"]}],
             "actions":[{"op":"move","target":"blue","by":[1.5,0],"start":.05,"end":.65},
                        {"op":"move","target":"yellow","by":[-.5,0],"start":.05,"end":.65},
                        {"op":"show","target":"sum","start":.7,"end":.9}]},
            {"type":"scene", "continue_previous":True, "heading":"移走两颗，观察剩下的珠子",
             "actions":[{"op":"hide","target":"sum","start":0,"end":.1},
                        {"op":"move","target":"yellow","by":[0,-1.5],"start":.1,"end":.7},
                        {"op":"highlight","target":"blue","start":.3,"end":.9},
                        {"op":"show","target":"difference","start":.7,"end":.95}]}]


def process_scene():
    return {"type":"scene", "heading":"观察空气中的水蒸气遇冷", "caption":"粒子运动仅作示意，不表示真实大小或轨迹",
            "objects":[
                {"id":"cup","kind":"path","points":[[-.9,.9],[-.7,-.9],[.7,-.9],[.9,.9]],"at":[-3,0],"color":"#94A3B8","label":"冷杯壁"},
                {"id":"water","kind":"rectangle","at":[-3,-.15],"size":[1.2,1.1],"fill":.65},
                {"id":"v1","kind":"circle","at":[1.2,.9],"size":[.25,.25],"fill":.8,"color":"#C4B5FD"},
                {"id":"v2","kind":"circle","at":[2.2,0],"size":[.25,.25],"fill":.8,"color":"#C4B5FD"},
                {"id":"v3","kind":"circle","at":[1.3,-.8],"size":[.25,.25],"fill":.8,"color":"#C4B5FD"},
                {"id":"drop","kind":"ellipse","at":[-2.1,-.1],"size":[.22,.4],"fill":1,"visible":False,"label":"小水珠"},
                {"id":"direction","kind":"arrow","at":[0,0],"size":[1.5,.4],"color":"#C4B5FD"}],
            "groups":[{"id":"gas","members":["v1","v2","v3"]}],
            "actions":[{"op":"rotate","target":"direction","degrees":180,"start":0,"end":.05},
                       {"op":"move","target":"gas","by":[-2.9,0],"start":.05,"end":.65},
                       {"op":"hide","target":"gas","start":.6,"end":.8},
                       {"op":"show","target":"drop","start":.6,"end":.85}]}


def spatial_scene():
    return {"type":"scene", "heading":"物体绕中心运动，再看整体的位置", "caption":"箭头和物体都由矢量图形组成",
            "objects":[
                {"id":"center","kind":"circle","size":[.5,.5],"fill":1,"color":"#FBBF24","label":"中心"},
                {"id":"route","kind":"circle","size":[3.5,3.5],"fill":0,"color":"#475569"},
                {"id":"moving","kind":"star","at":[1.75,0],"size":[.55,.55],"fill":.9,"label":"移动的物体"}],
            "actions":[{"op":"rotate","target":"moving","degrees":270,"about":[0,0],"start":0,"end":.7,"ease":"linear"},
                       {"op":"scale","target":"*","factor":.75,"about":[0,0],"start":.75,"end":1}]}


def language_scene():
    return {"type":"scene", "heading":"从行动理解一句话：把纸放进纸篓",
            "objects":[
                {"id":"head","kind":"circle","at":[-3,1],"size":[.45,.45],"fill":.8},
                {"id":"body","kind":"rectangle","at":[-3,.15],"size":[.4,1.1],"fill":.8},
                {"id":"leg1","kind":"line","at":[-3.2,-.75],"size":[.7,1]},
                {"id":"leg2","kind":"line","at":[-2.8,-.75],"size":[.7,1]},
                {"id":"paper","kind":"polygon","at":[-1,-.9],"points":[[-.3,-.18],[.3,-.18],[.23,.18],[-.23,.18]],"fill":.9,"color":"#E2E8F0"},
                {"id":"bin","kind":"path","at":[3,-.5],"points":[[-.6,.65],[-.45,-.65],[.45,-.65],[.6,.65]],"color":"#4ADE80","label":"纸篓"}],
            "groups":[{"id":"person","members":["head","body","leg1","leg2"]}],
            "actions":[{"op":"rotate","target":"leg1","degrees":70,"start":0,"end":.04},
                       {"op":"rotate","target":"leg2","degrees":110,"start":0,"end":.04},
                       {"op":"move","target":"person","by":[1.4,0],"start":.05,"end":.4},
                       {"op":"follow_path","target":"paper","points":[[0,0],[.2,1.4],[4,1.4],[4,.4]],"start":.4,"end":.95},
                       {"op":"highlight","target":"bin","color":"#FBBF24","start":.65,"end":1}]}


def lesson_fixture():
    visuals = [*counting_scenes(), process_scene(), spatial_scene(), language_scene()]
    return {"title":"图形动作回归", "question":"检查数量、变化过程、空间和语句动作的画面表达", "subject":"综合", "grade":"小学二年级",
            "segments":[{"id":f"s{i+1:02}", "narration":"这是一段用于检查动画与时间轴的测试音频。", "visual":visual} for i, visual in enumerate(visuals)]}
