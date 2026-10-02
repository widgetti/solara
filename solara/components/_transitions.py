import solara


@solara.component
def TransitionFlip(axis: str, show_first=True, children=[], duration=0.2):
    uid = solara.use_unique_key()[:6]
    name = f"rotate-{axis}-{uid}"
    css_code = f"""
.{name}-enter-active, .{name}-leave-active {{
  transition: all {duration}s ease-out;
  backface-visibility: hidden;
}}

.{name}-enter, .{name}-leave-to  {{
  transform: rotate{axis}(90deg);
}}
.{name}-enter-to, .{name}-leave {{
  transform: rotate{axis}(0deg);
}}
"""
    solara.Style(css_code)
    solara.Transition(show_first=show_first, name=name, duration=duration, children=children, mode="out-in")


@solara.component
def TransitionSlide(axis: str = "X", show_first=True, children=[], duration=0.2, translate_enter="50px", translate_leave="-50px"):
    uid = solara.use_unique_key()[:6]
    name = f"slide-{axis}-{uid}"
    css_code = f"""
.{name}-enter-active, .{name}-leave-active {{
  transition: all {duration}s ease-out !important;
}}

.{name}-enter {{
  transform: translate{axis}({translate_enter});
  opacity: 0;
}}

.{name}-leave-to  {{
  transform: translate{axis}({translate_leave});
  opacity: 0;
}}
.{name}-enter-to, .{name}-leave {{
  transform: translate{axis}(0px);
}}
"""
    print("css", css_code)
    solara.Style(css_code)
    solara.Transition(show_first=show_first, name=name, duration=duration, children=children, mode="out-in")
