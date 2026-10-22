"""Builds the Group B test prompts (Ref2VA six-part format, five-part shots) into prompts/*.txt.

Technique ported from the Seedance 2.5 showcase: the camera changes move every beat, every landed hit is an impact frame with a smear,
small random explosions rewrite the fight, every blast re-keys the palette, one strike per shot comes at the lens.
Format follows h3-video-prompting (origin/main): subject_definitions / summary / retention_analysis / detailed_description (+ five-part shots).
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "prompts"; OUT.mkdir(exist_ok=True)

SUBJECTS = """subject_definitions:
<Subject 1> is Kai, the cyborg brawler from <Picture 1>. Preserve his exact design: blond tousled hair, the orange LED visor over his eyes, the oversized beige sweatshirt, dark blue shorts, black mechanical arms and legs with orange and white armor plates, and heavy mechanical boots. <Picture 1> provides his character identity while his pose and background are adapted to the new fight.

<Subject 2> is Vex, the cyborg brawler from <Picture 2>. Preserve her exact design: white spiky hair with two black horn-like headphone spikes, red goggles, the red crop top and red shorts, a white mechanical right arm, a white mechanical left leg, and red spiked sneakers. <Picture 2> provides her character identity while her pose and background are adapted to the new fight.
"""

STYLE = ("High-sakuga 2D anime with bold linework, hard cel shading and speed smears. Kai stays the larger of the two; Vex stays lighter and quicker. "
         "The action runs continuously from the first frame to the last. Every landed hit snaps into a one-frame white-black impact flash while the struck body whips away in a smear and re-enters at once. "
         "Every blast re-colors the whole palette. When they close, one body is nearer the camera and the other clearly behind it with air between.")

SOUND = ("overall_soundscape:\nA bass drop on every impact, metal-on-metal clangs, sparks crackling, drums and cables exploding and then a second of muffled ringing, rain hiss, a distant siren, steam venting.\n\n"
         "non_diegetic_music:\nDriving cyberpunk percussion and low synth bass at a fast tempo, pulsing with each blast.")


def retention(shots):
    names = ", ".join(f"[Shot {i}]" for i in range(1, shots + 1))
    return ("retention_analysis:\n"
            f"<Subject 1> (appears in {names}): fully_preserved - Maintain the blond hair, orange LED visor, beige oversized sweatshirt, dark blue shorts, black mechanical limbs with orange and white plates, and the 2D anime linework throughout all visible shots.\n\n"
            f"<Subject 2> (appears in {names}): fully_preserved - Maintain the white spiky hair with black horn spikes, red goggles, red crop top and shorts, white mechanical right arm and left leg, red spiked sneakers, and the 2D anime linework throughout all visible shots.\n")


def build(summary, shots, five_part=True):
    body = [SUBJECTS, "summary:\n" + summary + "\n", retention(len(shots)), "detailed_description:\n" + STYLE + "\n"]
    for i, s in enumerate(shots, 1):
        stamp = "" if i == 1 else f"At {s['t']}, "
        head = f"[Shot {i}] {stamp}{s['head']}"
        if five_part:
            body.append(f"{head} Camera: {s['camera']} Motion: {s['motion']} Performance: {s['perf']} Light: {s['light']} Sound: {s['sound']}")
        else:
            body.append(f"{head} {s['motion']} {s['light']}")
    body.append(SOUND)
    return "\n\n".join(body).replace("\n\n\n", "\n\n") + "\n"


SCENE = ("Two cyborg fighters collide in a rain-lashed scrapyard at night under a half-collapsed gantry crane: stacked shipping containers at screen left, a row of oil drums along the lane, "
         "a sparking power-cable bundle hanging from the crane arm at screen right, a flooded gravel lane between them. Every small explosion around the yard rewrites the fight.")

# ---------------------------------------------------------------- B5: 5 s, 3 shots
B5 = [
    dict(t="", head="Low-angle wide shot (24mm, two metres, ankle height) of <Subject 1> and <Subject 2> already airborne over the flooded lane, as the camera rockets upward through the gap between them with large amplitude at fast speed.",
         camera="24mm at ankle height, a fast large-amplitude rise from puddle level to chest level through the gap between the bodies, ending with both fighters in the upper thirds and the gantry crane filling the background.",
         motion="<Subject 1> drives his black mechanical right fist forward from a planted rear boot while <Subject 2> twists in mid-air and thrusts her red spiked sneaker; fist and sole meet at about 0.6 s in a one-frame white-black impact flash with sparks, both bodies smear backward, then their feet plant and push off again.",
         perf="His jaw sets behind the visor glow; her teeth show in a tight grin under the goggles.",
         light="Orange from his visor and the sparks, cold blue rain light from above, water drops freezing white in the flash.",
         sound="A metal-on-sole crack at about 0.6 s with a bass drop under it, rain hiss continuing."),
    dict(t="00:01.700", head="Tight side view (35mm, one metre, shoulder height) of both bodies still smeared from the clash, as the camera crash-zooms toward the hit point with large amplitude at fast speed.",
         camera="35mm at shoulder height, a fast large-amplitude crash-in that lands with the chin line of <Subject 1> on the left third and her rising fist on the right third.",
         motion="<Subject 1> throws a left hook; <Subject 2> ducks beneath it as an oil drum beside her bursts apart unannounced and hurls her upward, and she rides that lift into a white mechanical-arm uppercut under his chin; his head snaps back into a smear and the visor draws an orange arc through the rain.",
         perf="His visor glow flares bright and his mouth opens on a grunt; her brow drops low, all attention on the next hit.",
         light="Burst of drum fire lights both faces from below in orange, rain streaks turn into glowing lines.",
         sound="The drum blast at about 0.3 s, then a hard bone-and-metal crack at about 0.7 s, ears ringing for a beat."),
    dict(t="00:03.600", head="Wide low angle (20mm, three metres, ground height) of the lane and the crane as the camera whips sideways with the shockwave with large amplitude at fast speed.",
         camera="20mm at ground height, a fast large-amplitude sideways whip that lands with both fighters on opposite thirds and the cable bundle overhead.",
         motion="The power-cable bundle snaps free of the crane and whips across the lane in a blue-white arc blast that hurls both fighters left and right toward the containers; they rebound off the steel at the same moment and leap at each other through the arcing sparks, fists forward, still in motion as the frame ends.",
         perf="Both bodies stay tight and fully committed; his visor glow stretches into a line as he launches.",
         light="The whole palette re-keys from orange to blue-white, cold arc light rims both silhouettes, rain turns to silver needles.",
         sound="A crackling arc blast at about 0.2 s, a bass drop, then a rising whine as the fists close."),
]

# ---------------------------------------------------------------- B10: 10 s, 5 shots
B10 = [
    dict(t="", head="Wide low angle (24mm, two metres, ankle height) of <Subject 1> and <Subject 2> airborne over the flooded lane, as the camera rockets upward between them with large amplitude at fast speed.",
         camera="24mm at ankle height, a fast large-amplitude rise from puddle level to chest level through the gap, ending with the crane arm filling the top third.",
         motion="<Subject 1> throws a black mechanical right fist and <Subject 2> meets it with the sole of her red spiked sneaker in mid-air; the contact lands as a one-frame white-black impact flash with sparks, both bodies smear backward, feet plant, and they lunge again.",
         perf="His jaw sets behind the visor glow; her teeth show in a tight grin under the goggles.",
         light="Orange from his visor and sparks against cold blue rain light from above.",
         sound="A metal-on-sole crack at about 0.6 s with a bass drop under it, rain hiss."),
    dict(t="00:01.800", head="Ground-level side view (28mm, 1.5 metres) of the lane as the camera crash-zooms to the hit point with large amplitude at fast speed.",
         camera="28mm at ground height, a fast large-amplitude crash-in on the hit point with the drum row at the right third.",
         motion="<Subject 1> throws a left hook; <Subject 2> ducks as a drum bursts beside her and the blast throws her up into his chin with a white mechanical-arm uppercut; his head snaps into a smear, visor drawing an orange arc, and he answers with a spinning heel that sweeps her ribs and folds her sideways before she plants and springs back.",
         perf="His visor glow flares bright and his jaw clenches; her brow drops low and she keeps her eyes on his hips.",
         light="Drum fire underlights both faces in orange, rain streaks glow.",
         sound="Drum blast at about 0.3 s, a bone-and-metal crack at about 0.8 s, then a second of muffled ringing."),
    dict(t="00:04.000", head="Tracking shot (24mm, waist height) racing between the stacked containers as the camera follows the fighters bounding up the steel with large amplitude at fast speed.",
         camera="24mm at waist height, a fast large-amplitude sweep upward along the container faces that tops out at their roofs with both fighters on the upper thirds.",
         motion="Both leap onto the container wall, <Subject 2> spins off a corner into a white mechanical-arm sweep, <Subject 1> ducks and his fist punches a container door into a spray of rusted fragments, and her spiked sneaker is already kicking through the debris; he blocks on his black mechanical arm and is driven back along the roof edge.",
         perf="His breath puffs white as he braces; her eyes narrow as she reads the block.",
         light="Sparks from the torn steel, a sodium streetlamp throwing amber across wet containers.",
         sound="Shearing metal at about 0.5 s, a spiked-sole scrape, heavy boots landing."),
    dict(t="00:06.200", head="Top-down wide (14mm, thirty metres) of the whole scrapyard as the camera pulls far back with the blast with large amplitude at fast speed.",
         camera="14mm from a crane-top height, a fast large-amplitude pull-back that frames the full yard with both fighters as small figures.",
         motion="A container stack erupts from deep inside, the fireball climbs toward the crane arm, both fighters are thrown into the air with rain, crates and burning fuel spiralling around them, and from mid-air <Subject 2> grabs <Subject 1> by the collar and lands a headbutt on his visor before he flips back and kicks her white mechanical leg with a spray of sparks.",
         perf="His visor flickers on the impact; her lips pull back in a snarl as she hits.",
         light="The fireball rekeys the palette to deep orange and black, firelight crawling over the wet ground far below.",
         sound="A rolling blast at about 0.3 s, then a muffled ring, then rain and metal creaking."),
    dict(t="00:08.300", head="Point-of-view view (18mm, face height) from between the two fighters as the camera tumbles with them with large amplitude at fast speed.",
         camera="18mm at face height, a fast large-amplitude tumble that ends with her spiked sole filling the lens.",
         motion="Burning fuel tears open into a ball around <Subject 1>'s fist, <Subject 2>'s red spiked sole rushes straight at the lens, then the crane groans and drops a chain across the lane and both slam onto the gravel and roll up already moving into the next lunge, still in motion as the frame ends.",
         perf="His mouth opens in a shout beneath the visor glow; her goggles reflect the fire.",
         light="Fire-orange on both faces, the chain throwing a long moving shadow across the lane.",
         sound="A swallowed boom at about 0.4 s, a chain rattle, gravel crunching under landing boots."),
]

# ---------------------------------------------------------------- B15: 15 s, 6 shots
B15 = [
    dict(t="", head="Wide low angle (24mm, two metres, ankle height) of <Subject 1> and <Subject 2> airborne over the flooded lane, as the camera rockets upward through the gap between them with large amplitude at fast speed.",
         camera="24mm at ankle height, a fast large-amplitude rise from puddle level to chest level through the gap, ending with the crane arm filling the top third.",
         motion="<Subject 1> drives his black mechanical right fist forward from a planted rear boot while <Subject 2> twists in mid-air and thrusts her red spiked sneaker; fist and sole meet at about 0.6 s in a one-frame white-black impact flash with sparks, both bodies smear backward, feet plant and push, and they lunge again.",
         perf="His jaw sets behind the visor glow; her teeth show in a tight grin under the goggles.",
         light="Orange from his visor and the sparks, cold blue rain light from above, water drops freezing white in the flash.",
         sound="A metal-on-sole crack at about 0.6 s with a bass drop under it, rain hiss continuing."),
    dict(t="00:02.000", head="Tight side view (35mm, one metre, shoulder height) of both bodies still smeared from the clash, as the camera crash-zooms to the hit point with large amplitude at fast speed.",
         camera="35mm at shoulder height, a fast large-amplitude crash-in that lands on the chin line of <Subject 1> with the drum row at the right third.",
         motion="<Subject 1> throws a left hook; <Subject 2> ducks beneath it as a drum beside her bursts apart unannounced and hurls her upward, and she rides the lift into a white mechanical-arm uppercut under his chin; his head snaps into a smear with the visor drawing an orange arc, and he answers with a spinning heel that sweeps her ribs and folds her sideways before she plants and springs back.",
         perf="His visor glow flares bright and his mouth opens on a grunt; her brow drops low, her eyes on his hips for the next opening.",
         light="Burst of drum fire lights both faces from below in orange, rain streaks turn into glowing lines.",
         sound="The drum blast at about 0.3 s, a hard bone-and-metal crack at about 0.8 s, then a second of muffled ringing."),
    dict(t="00:04.500", head="Tracking shot (24mm, waist height) racing between the stacked containers as the camera follows the fighters bounding up the steel with large amplitude at fast speed.",
         camera="24mm at waist height, a fast large-amplitude sweep upward along the container faces that tops out at the roofs with both fighters on the upper thirds.",
         motion="Both leap onto the container wall, <Subject 2> spins off a corner into a white mechanical-arm sweep, <Subject 1> ducks and his fist punches a container door into a spray of rusted fragments, her spiked sneaker already kicking through the debris; a second blast tears a hole in the roof beneath his lead foot so he drops half through, and she drives the sole into his unbalanced body; he blocks on his black mechanical arm and is thrown back across the roof edge.",
         perf="His breath puffs white as he braces; her eyes narrow as she reads the block and the hole at once.",
         light="Sparks from the torn steel, a sodium streetlamp throwing amber across wet containers, the blast rekeying the frame to hot orange for a beat.",
         sound="Shearing metal at about 0.5 s, a blast at about 1.4 s, a spiked-sole scrape, heavy boots landing."),
    dict(t="00:07.500", head="Top-down wide (14mm, thirty metres) of the whole scrapyard as the camera pulls far back with the blast with large amplitude at fast speed.",
         camera="14mm from crane-top height, a fast large-amplitude pull-back that frames the full yard with both fighters as small figures.",
         motion="A container stack erupts from deep inside, the fireball climbs toward the crane arm, and both fighters are thrown into the air with rain, crates and burning fuel spiralling around them; from mid-air <Subject 2> grabs <Subject 1> by the collar and lands a headbutt on his visor before he flips back and kicks her white mechanical leg with a spray of sparks, and they kick off each other across the burning yard.",
         perf="His visor flickers on the impact; her lips pull back in a snarl as she hits.",
         light="The fireball rekeys the palette to deep orange and black, firelight crawling over the wet ground far below.",
         sound="A rolling blast at about 0.3 s, then a muffled ring, then rain and metal creaking."),
    dict(t="00:10.500", head="High-angle view (20mm, six metres, descending to chest height) onto the lane as the camera trucks left while panning right around the crossing limbs with large amplitude at fast speed.",
         camera="20mm descending from six metres to chest height, a fast large-amplitude truck-and-pan that finishes with both fighters in a tight two-shot.",
         motion="The power-cable bundle snaps free of the crane and whips across the lane in a blue-white arc blast that slams <Subject 2> into the container wall; she rebounds off the steel into a white mechanical-leg spinning kick to <Subject 1>'s temple, his visor drawing a line as his head swings, and he turns the swing into a back-fist that lands on her collarbone and drives her shoulder down.",
         perf="His visor flickers and his teeth clench; her eyes squeeze shut on impact and snap open already angry.",
         light="The whole palette re-keys to blue-white, cold arc light rims both silhouettes, rain turns to silver needles.",
         sound="A crackling arc blast at about 0.2 s, a bass drop, a wet crack at about 1.1 s."),
    dict(t="00:13.000", head="Low-angle close view (28mm, 1.2 metres) as the camera dives under the kick with large amplitude at fast speed.",
         camera="28mm at knee height, a fast large-amplitude dive beneath the kick path, riding the final blast and ending with a fist filling the lens.",
         motion="A last drum blast throws <Subject 2> sideways into <Subject 1>'s straight punch; she takes it on her white mechanical arm, which throws sparks and shakes, and counters with a knee; he side-steps, drives his head into her forehead, her head snaps back into a smear, and her white fist cracks his visor; he staggers two steps, plants, and his black fist comes straight at the lens, still in motion as the frame ends.",
         perf="His visor crackles and his lip curls; her expression flips from pain to fury in a heartbeat.",
         light="Fire-orange flashes across both faces, cracked visor light leaking orange onto his cheek.",
         sound="A swallowed boom at about 0.4 s, a visor crack at about 1.6 s, gravel crunching under landing boots."),
]

B15_SUMMARY = "[reference generation] " + SCENE


def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8")
    words = len(text.split())
    print(f"{name}: {len(text)} chars, {words} words")


write("b5-scrapyard-5s.txt", build("[reference generation] " + SCENE, B5))
write("b10-scrapyard-10s.txt", build("[reference generation] " + SCENE, B10))
write("b15-scrapyard-15s.txt", build(B15_SUMMARY, B15))


# ---------------------------------------------------------------- B15 compressed: the skill's <=700-word budget (one sentence per shot, no five-part labels)
SHORT15 = [
    ("", "Wide low angle of <Subject 1> and <Subject 2> airborne over the flooded lane, as the camera rockets upward through the gap between them with large amplitude at fast speed. Fist and spiked sole meet in a one-frame white-black impact flash with sparks, both bodies smear backward, feet plant, and they lunge again."),
    ("00:02.000", "Tight side view as the camera crash-zooms to the hit point with large amplitude at fast speed. A drum bursts beside <Subject 2> and throws her up into a white mechanical-arm uppercut under <Subject 1>'s chin; his head snaps into a smear, the visor draws an orange arc, and he answers with a spinning heel."),
    ("00:04.500", "Tracking shot at waist height between stacked containers as the camera follows the fighters bounding up the steel with large amplitude at fast speed. <Subject 1> punches a container door into fragments, a blast opens the roof under his lead foot, and <Subject 2>'s spiked sole drives into his unbalanced body."),
    ("00:07.500", "Top-down wide of the whole scrapyard as the camera pulls far back with the blast with large amplitude at fast speed. A container stack erupts, both fighters are thrown into the air with burning fuel spiralling around them, and <Subject 2> lands a headbutt on his visor before he kicks her white mechanical leg."),
    ("00:10.500", "High-angle view onto the lane as the camera trucks left while panning right around the crossing limbs with large amplitude at fast speed. A snapped cable whips a blue-white arc blast that slams <Subject 2> into the container wall; she rebounds into a spinning kick to <Subject 1>'s temple and he answers with a back-fist."),
    ("00:13.000", "Low-angle close view as the camera dives under the kick with large amplitude at fast speed. A last drum blast throws <Subject 2> into his straight punch; she counters with a knee and a white fist that cracks his visor, and his black fist comes straight at the lens, still in motion as the frame ends."),
]


def build_compact():
    body = [SUBJECTS, "summary:\n" + B15_SUMMARY + "\n", retention(len(SHORT15)),
            "detailed_description:\n" + STYLE + "\n"]
    for i, (t, text) in enumerate(SHORT15, 1):
        body.append(f"[Shot {i}] " + ("" if i == 1 else f"At {t}, ") + text)
    body.append(SOUND)
    return "\n\n".join(body) + "\n"


write("b15-scrapyard-15s-oneline.txt", build_compact())
