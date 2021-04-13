# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; version 3
#  of the License.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

from difflib import SequenceMatcher
from bpy.props import IntProperty, CollectionProperty, StringProperty, BoolProperty
import bpy

bl_info = {
    "name": "Text Markers",
    "author": "Samy Tichadou (tonton)/reviewed by 1C0D",
    "version": (1, 2, 1),
    "blender": (2, 80, 0),
    "location": "Text Editor > ToolShelf > Text Markers",
    "description": "Use Text Markers to keep your scripts organised",
    "wiki_url": "https://github.com/samytichadou/TextMarker-blender-addon/wiki",
    "tracker_url": "https://github.com/samytichadou/TextMarker-blender-addon/issues/new",
    "category": "Development",
}


# Create custom property group
class TMItems(bpy.types.PropertyGroup):

    linenumber: IntProperty(name="linenumber")
    linecontent: StringProperty(name="linecontent")
    linesbefore: StringProperty(name="linesbefore")
    linesafter: StringProperty(name="linesafter")
    linemissing: BoolProperty(name="linemissing", default=False)


class TMProperties(bpy.types.PropertyGroup):

    def jumpto(self, context):
        if self.autojump:
            txt = context.space_data.text
            idx= self.index
            items = txt.tm.list
            item = txt.tm.list[idx]
            bpy.ops.text.jump(line=item.linenumber)

    def update_search(self, context):
        bpy.ops.textmarker.add_fromsearch()

    list: CollectionProperty(type=TMItems)
    index: IntProperty(update=jumpto)
    autojump: BoolProperty(
        default=True, description="Jump text cursor to selected marker"
    )
    searchterm: StringProperty(
        description="Add Markers by keyword (Enter to confirm)",
        default="Enter to confirm",
        update=update_search,
        maxlen=100,
    )


# UILIST
class TEXTMARKER_UL_List(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):

        label = str(item.linenumber)
        u = layout.row()
        c = u.column()
        r = u.column().row(align=True)
        r.prop(item, "name", text=label, emboss=False)
        updown = r.column(align=True)
        updown.scale_y = 0.5
        op = updown.operator(
            "textmarker.actions", text="", icon="TRIA_UP", emboss=False
        )
        op.target = index
        op.action = "UP"
        op = updown.operator(
            "textmarker.actions", text="", icon="TRIA_DOWN", emboss=False
        )
        op.target = index
        op.action = "DOWN"


# Draw Panel
class TEXTMARKER_PT_panel(bpy.types.Panel):
    bl_space_type = "TEXT_EDITOR"
    bl_region_type = "UI"
    bl_category = "Markers"
    bl_label = "Text Markers"

    def draw(self, context):
        layout = self.layout
        texts = bpy.data.texts
        if len(texts):
            txt = context.space_data.text.tm
            items = txt.list
            idx= txt.index

            row = layout.row()
            row.prop(txt, "autojump", icon="AUTO", text="")
            row.prop(txt, "searchterm", icon="VIEWZOOM", text="")
            row = layout.row()
            row.operator("textmarker.actions", icon="ADD", text="").action = "ADD"
            op = row.operator("textmarker.actions", text="", icon="REMOVE")
            op.action = "DEL"
            row.operator("textmarker.sort", icon="SORTSIZE", text="")
            row.operator("textmarker.clear_all", icon="X", text="Clear All")
            row.operator(
                "textmarker.clear_missing_update", icon="FILE_REFRESH", text=""
            )

            row = layout.row()
            row.template_list("TEXTMARKER_UL_List", "", txt, "list", txt, "index", rows=8)

            if len(items):
                row = layout.row()
                row = row.box()
                row.label(text=("" + (items[idx].linecontent).strip()))

            row = layout.row(align=True)

        else:
            row = layout.row()
            row.label(text="No Text loaded", icon="INFO")


# ui list category actions
class TEXTMARKER_MT_actions(bpy.types.Operator):
    bl_idname = "textmarker.actions"
    bl_label = ""
    bl_description = "Text Markers actions"

    target: bpy.props.IntProperty(name="Target Item Index")

    action: bpy.props.EnumProperty(
        items=(
            ("ADD", "Add", ""),
            ("DEL", "Del", ""),
            ("DEL1", "Del1", ""),
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("NEXT", "Next", ""),
            ("PREVIOUS", "Previous", ""),
        )
    )

    def clamp(self, n, length):
        return max(min(length, n), 0)  # (min of max max of min)

    def invoke(self, context, event):
        bpy.ops.text.cursor_set("INVOKE_DEFAULT")
        return self.execute(context)

    def execute(self, context):
        txt = context.space_data.text
        idx = txt.tm.index
        items = txt.tm.list
        length = len(items)
        cli = txt.current_line_index

        if self.action == "ADD" and txt.lines[cli].body:
            ####update()
            for item in items:
                if item.linenumber == cli + 1:
                    info = " Marker already exists"
                    self.report({"WARNING"}, info)
                    return {"CANCELLED"}

            newmarker = items.add()
            newmarker.linecontent = txt.lines[cli].body.strip()
            newmarker.name = newmarker.linecontent[:30]
            newmarker.linenumber = cli + 1

            beforecontent = ""
            aftercontent = ""
            for n in range(1, 11):
                if cli - n >= 0:
                    newmarker.linesbefore += txt.lines[cli - n].body
                elif cli + n < len(txt.lines):
                    newmarker.linesafter += txt.lines[cli + n].body

            txt.tm.index = length

        elif self.action == "UP":

            newindex = self.clamp(self.target - 1, length)

            if idx!= 0 and idx== self.target:
                txt.tm.index -= 1  # highlight up

            if self.target == idx+ 1:  # if previous highlighted
                txt.tm.index += 1  # highlight down

            items.move(self.target, newindex)

        elif self.action == "DOWN":

            newindex = self.clamp(self.target + 1, length)

            if idx!= len(items) - 1 and idx== self.target:
                txt.tm.index += 1

            elif self.target == idx- 1:
                txt.tm.index -= 1

            items.move(self.target, newindex)

        elif self.action == "DEL" and txt.lines[cli].body:
            items.remove(idx)


        elif self.action == "DEL1" and txt.lines[cli].body:
            for i, item in enumerate(items):
                if item.linenumber == cli + 1:
                    items.remove(i)
                    break
            context.area.tag_redraw()

        return {"FINISHED"}


# Sort list by linenumber
class TEXTMARKER_OT_sort(bpy.types.Operator):
    bl_idname = "textmarker.sort"
    bl_label = ""
    bl_description = "Sort Text Markers by Line Number"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        txt = context.space_data.text
        text = bpy.data.texts
        items = txt.tm.list
        return len(items)

    def execute(self, context):
        txt = context.space_data.text
        items = txt.tm.list
        idx= txt.tm.index
        name = []
        line = []
        content = []
        missing = []
        after = []
        before = []

        nlist = sorted(items, key=lambda x: x.linenumber, reverse=False)

        for n in nlist:
            name.append(str(n.name))
            line.append(str(n.linenumber))
            content.append(n.linecontent)
            missing.append(n.linemissing)
            after.append(n.linesafter)
            before.append(n.linesbefore)

        items.clear()

        for i,n in enumerate(name):
            new = items.add()
            new.name = n
            new.linenumber = int(line[i])
            new.linecontent = content[i]
            new.linemissing = missing[i]
            new.linesafter = after[i]
            new.linesbefore = before[i]

        return {"FINISHED"}


def tm_update(self, context):
    txt = context.space_data.text
    items = txt.tm.list
    idx= txt.tm.index

    for item in items:
        possible = []
        simila = []
        similb = []

        for i, line in enumerate(txt.lines, start=1):
            l2 = item.linecontent.strip()
            if l2 in line.body:
                possible.append(i)
        
        if not possible:
            item.linemissing = True
            return

        for p in possible:
            before = "".join(
                txt.lines[i].body for i in range(p - 11, p - 1) if i >= 0
            )
            after = "".join(
                txt.lines[i].body for i in range(p, p + 10) if i < len(txt.lines)
            )

            pctb = SequenceMatcher(None, before, item.linesbefore).ratio()
            pcta = SequenceMatcher(None, after, item.linesafter).ratio()
            simila.append(pcta)
            similb.append(pctb)

        if possible:
            oka = max(simila)
            okb = max(similb)
            if simila.index(oka) == similb.index(okb):
                okidx = simila.index(oka)
            else:
                okidx = simila.index(oka) if oka > okb else similb.index(okb)

        item.linenumber = possible[okidx]
        item.linecontent = txt.lines[possible[okidx] - 1].body

        beforecontent = ""
        aftercontent = ""
        for n in range(1, 11):
            if (item.linenumber - 1) - n >= 0:
                beforecontent += txt.lines[(item.linenumber - 1) - n].body
            elif (item.linenumber - 1) + n < len(txt.lines):
                aftercontent += txt.lines[(item.linenumber - 1) + n].body
                
        item.linesafter = aftercontent
        item.linesbefore = beforecontent

    testdupe = [item.linenumber for item in items]

    for i, item in enumerate(items):
        chk = sum(item.linenumber == n for n in testdupe)
        if chk >= 2:
            items.remove(i)


# Clear Missing Lines and update Markers
class TEXTMARKER_OT_clear_missing_update(bpy.types.Operator):
    bl_idname = "textmarker.clear_missing_update"
    bl_label = ""
    bl_description = "Delete missing Markers from list"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        txt = context.space_data.text
        text = bpy.data.texts
        items = txt.tm.list
        return len(items)

    def execute(self, context):
        txt = context.space_data.text
        items = txt.tm.list

        tm_update(self, context)  # missing lines

        for i, item in enumerate(items):
            if item.linemissing:
                items.remove(i)

        tm_update(self, context)  # again after remove

        return {"FINISHED"}


# Add Marker from term search
class TEXTMARKER_OT_add_from_search(bpy.types.Operator):
    bl_idname = "textmarker.add_fromsearch"
    bl_label = ""
    bl_description = "Search keyword and add as Markers"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        txt = context.space_data.text
        text = bpy.data.texts
        return txt.tm.searchterm

    def execute(self, context):
        txt = context.space_data.text
        items = txt.tm.list
        term = txt.tm.searchterm

        for i, line in enumerate(txt.lines, start=1):
            if term in line.body:
                for item in items:
                    if item.linenumber == i:
                        break

                newmarker = items.add()
                content = line.body.lstrip()
                newmarker.name = content[:35]
                newmarker.linecontent = line.body
                newmarker.linenumber = i
                beforecontent = ""
                aftercontent = ""
                for n in range(1, 11):
                    if (newmarker.linenumber - 1) - n >= 0:
                        beforecontent += txt.lines[
                            (newmarker.linenumber - 1) - n
                        ].body
                    if (newmarker.linenumber - 1) + n < len(txt.lines):
                        aftercontent += txt.lines[
                            (newmarker.linenumber - 1) + n
                        ].body
                newmarker.linesbefore = beforecontent
                newmarker.linesafter = aftercontent

        return {"FINISHED"}


# Clear All Markers
class TEXTMARKER_OT_clear_all(bpy.types.Operator):
    bl_idname = "textmarker.clear_all"
    bl_label = ""
    bl_description = "Delete all Markers from list"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        txt = context.space_data.text
        text = bpy.data.texts
        items = txt.tm.list
        return len(items)

    def execute(self, context):

        txt = context.space_data.text
        items = txt.tm.list
        items.clear()

        return {"FINISHED"}


classes = [
    TMItems,
    TMProperties,
    TEXTMARKER_UL_List,
    TEXTMARKER_PT_panel,
    TEXTMARKER_MT_actions,
    TEXTMARKER_OT_sort,
    TEXTMARKER_OT_clear_missing_update,
    TEXTMARKER_OT_add_from_search,
    TEXTMARKER_OT_clear_all,
]

keymaps = []

# register
def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Text.tm = bpy.props.PointerProperty(type=TMProperties)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is not None:
        km = kc.keymaps.new(name="Text", space_type="TEXT_EDITOR")
        kmi = km.keymap_items.new("textmarker.actions", "LEFTMOUSE", "PRESS", alt=1)
        kmi.properties.action = "ADD"
        keymaps.append((km, kmi))

        kmi = km.keymap_items.new("textmarker.actions", "RIGHTMOUSE", "PRESS", alt=1)
        kmi.properties.action = "DEL1"
        keymaps.append((km, kmi))


# unregister
def unregister():

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is not None:
        for km, kmi in keymaps:
            km.keymap_items.remove(kmi)

    del bpy.types.Text.tm

    for c in reversed(classes):
        bpy.utils.unregister_class(c)
