__version__ = "0.1.0"

import sqlite3
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle


BG = (0.055, 0.063, 0.09, 1)
CARD = (0.095, 0.11, 0.16, 1)
CARD_ALT = (0.12, 0.135, 0.20, 1)
PURPLE = (0.51, 0.36, 0.95, 1)
PURPLE_DARK = (0.32, 0.22, 0.68, 1)
GREEN = (0.26, 0.78, 0.53, 1)
TEXT = (0.94, 0.95, 1, 1)
MUTED = (0.62, 0.65, 0.75, 1)
GOLD = (1.0, 0.73, 0.25, 1)


class RoundedBox(BoxLayout):
    bg_color = CARD
    radius = dp(18)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class FlatButton(Button):
    def __init__(self, **kwargs):
        bg = kwargs.pop("bg", PURPLE)
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = bg
        self.color = TEXT
        self.font_size = "15sp"
        self.bold = True
        self.size_hint_y = None
        self.height = dp(48)


class LifeDB:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.seed()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            xp INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            xp INTEGER NOT NULL,
            rarity TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            custom INTEGER NOT NULL DEFAULT 0
        );

        INSERT OR IGNORE INTO profile(id, xp) VALUES (1, 0);
        """)
        self.conn.commit()

    def seed(self):
        count = self.conn.execute("SELECT COUNT(*) FROM achievements").fetchone()[0]
        if count:
            return
        samples = [
            ("Первый шаг", "Выполни первую ачивку в приложении", "Старт", 25, "Обычная"),
            ("Ранний подъём", "Встань до 07:00 три раза", "Режим", 60, "Редкая"),
            ("Без откладываний", "Закрой важную задачу, которую давно переносил", "Продуктивность", 80, "Редкая"),
            ("Неделя движения", "Занимайся физической активностью 3 раза за неделю", "Здоровье", 100, "Эпическая"),
            ("Книжный червь", "Прочитай одну книгу полностью", "Развитие", 120, "Эпическая"),
            ("Мастер привычки", "Поддерживай одну полезную привычку 30 дней", "Привычки", 300, "Легендарная"),
        ]
        self.conn.executemany(
            """INSERT INTO achievements(title, description, category, xp, rarity)
               VALUES (?, ?, ?, ?, ?)""",
            samples,
        )
        self.conn.commit()

    def get_profile(self):
        xp = self.conn.execute("SELECT xp FROM profile WHERE id=1").fetchone()["xp"]
        level = xp // 250 + 1
        level_xp = xp % 250
        return {"xp": xp, "level": level, "level_xp": level_xp, "next": 250}

    def list_achievements(self, completed=None):
        if completed is None:
            q = "SELECT * FROM achievements ORDER BY completed, custom DESC, id DESC"
            return self.conn.execute(q).fetchall()
        return self.conn.execute(
            "SELECT * FROM achievements WHERE completed=? ORDER BY id DESC",
            (int(completed),),
        ).fetchall()

    def add_achievement(self, title, description, category, xp, rarity):
        self.conn.execute(
            """INSERT INTO achievements(title, description, category, xp, rarity, custom)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (title, description, category, xp, rarity),
        )
        self.conn.commit()

    def complete(self, achievement_id):
        row = self.conn.execute(
            "SELECT * FROM achievements WHERE id=?", (achievement_id,)
        ).fetchone()
        if not row or row["completed"]:
            return 0
        self.conn.execute(
            "UPDATE achievements SET completed=1, completed_at=? WHERE id=?",
            (datetime.now().isoformat(timespec="minutes"), achievement_id),
        )
        self.conn.execute(
            "UPDATE profile SET xp=xp+? WHERE id=1", (row["xp"],)
        )
        self.conn.commit()
        return row["xp"]


def txt(text, size=16, color=TEXT, bold=False, **kwargs):
    label = Label(
        text=text,
        color=color,
        font_size=f"{size}sp",
        bold=bold,
        markup=True,
        halign=kwargs.pop("halign", "left"),
        valign=kwargs.pop("valign", "middle"),
        **kwargs,
    )
    label.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width, None)))
    return label


class AchievementCard(RoundedBox):
    def __init__(self, row, on_complete=None, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(9),
            size_hint_y=None,
            **kwargs,
        )
        self.row = row
        self.height = dp(190 if not row["completed"] else 160)

        top = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        rarity_color = {
            "Обычная": MUTED,
            "Редкая": (0.32, 0.65, 1, 1),
            "Эпическая": PURPLE,
            "Легендарная": GOLD,
        }.get(row["rarity"], MUTED)

        rarity = txt(f"[b]{row['rarity']}[/b]", 12, rarity_color, markup=True)
        category = txt(row["category"], 12, MUTED, halign="right")
        top.add_widget(rarity)
        top.add_widget(category)
        self.add_widget(top)

        self.add_widget(txt(row["title"], 19, TEXT, True, size_hint_y=None, height=dp(34)))
        self.add_widget(txt(row["description"], 14, MUTED, size_hint_y=None, height=dp(48)))

        bottom = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        bottom.add_widget(txt(f"+{row['xp']} XP", 15, GOLD, True))
        if row["completed"]:
            bottom.add_widget(txt("✓ Выполнено", 14, GREEN, True, halign="right"))
        else:
            btn = FlatButton(text="Выполнить", bg=PURPLE_DARK)
            btn.size_hint_x = 0.48
            btn.bind(on_release=lambda *_: on_complete(row["id"]) if on_complete else None)
            bottom.add_widget(btn)
        self.add_widget(bottom)


class HomeScreen(Screen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.root_box = BoxLayout(
            orientation="vertical",
            padding=[dp(16), dp(18), dp(16), dp(10)],
            spacing=dp(12),
        )
        self.add_widget(self.root_box)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        self.root_box.clear_widgets()
        profile = self.app_ref.db.get_profile()

        header = BoxLayout(size_hint_y=None, height=dp(62))
        title_box = BoxLayout(orientation="vertical")
        title_box.add_widget(txt("LIFE QUEST", 24, TEXT, True))
        title_box.add_widget(txt("Прокачивай реальную жизнь", 13, MUTED))
        header.add_widget(title_box)
        level = txt(f"УР. {profile['level']}", 16, GOLD, True, halign="right")
        header.add_widget(level)
        self.root_box.add_widget(header)

        stats = RoundedBox(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(8),
            size_hint_y=None,
            height=dp(112),
            bg_color=CARD_ALT,
        )
        stats.add_widget(txt(f"[b]{profile['xp']} XP[/b] всего", 18, TEXT, markup=True))
        stats.add_widget(txt(
            f"До следующего уровня: {profile['next'] - profile['level_xp']} XP",
            13, MUTED
        ))
        bar_outer = RoundedBox(size_hint_y=None, height=dp(13), padding=0, bg_color=(0.18,0.19,0.27,1))
        progress = profile["level_xp"] / profile["next"]
        bar_inner = RoundedBox(size_hint_x=max(progress, 0.02), bg_color=PURPLE, padding=0)
        bar_outer.add_widget(bar_inner)
        if progress < 1:
            bar_outer.add_widget(Widget(size_hint_x=1-progress))
        stats.add_widget(bar_outer)
        self.root_box.add_widget(stats)

        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        add_btn = FlatButton(text="+ Своя ачивка")
        add_btn.bind(on_release=lambda *_: self.app_ref.open_add())
        history_btn = FlatButton(text="История", bg=CARD_ALT)
        history_btn.bind(on_release=lambda *_: self.app_ref.show_history())
        actions.add_widget(add_btn)
        actions.add_widget(history_btn)
        self.root_box.add_widget(actions)

        self.root_box.add_widget(txt("Доступные ачивки", 18, TEXT, True, size_hint_y=None, height=dp(32)))

        scroll = ScrollView(bar_width=dp(3))
        cards = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        cards.bind(minimum_height=cards.setter("height"))
        rows = self.app_ref.db.list_achievements(completed=False)
        if not rows:
            cards.add_widget(txt("Все ачивки выполнены 🎉", 17, GREEN, True, size_hint_y=None, height=dp(80)))
        for row in rows:
            cards.add_widget(AchievementCard(row, self.complete))
        scroll.add_widget(cards)
        self.root_box.add_widget(scroll)

    def complete(self, achievement_id):
        gained = self.app_ref.db.complete(achievement_id)
        if gained:
            popup = Popup(
                title="Ачивка выполнена!",
                content=txt(f"Ты получил [b]+{gained} XP[/b] 🎉", 18, GOLD, markup=True, halign="center"),
                size_hint=(0.82, None),
                height=dp(220),
            )
            popup.open()
        self.refresh()


class AddScreen(Screen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        root = BoxLayout(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12),
        )
        root.add_widget(txt("Создать ачивку", 25, TEXT, True, size_hint_y=None, height=dp(52)))

        self.title_input = self.make_input("Название")
        self.desc_input = self.make_input("Описание", multiline=True, height=dp(110))
        self.category_input = self.make_input("Категория, например: Работа")
        self.xp_input = self.make_input("Опыт: 10–1000", input_filter="int")
        self.rarity_input = self.make_input("Редкость: Обычная / Редкая / Эпическая / Легендарная")

        for widget in (
            self.title_input, self.desc_input, self.category_input,
            self.xp_input, self.rarity_input
        ):
            root.add_widget(widget)

        root.add_widget(Widget())
        save = FlatButton(text="Сохранить ачивку")
        save.bind(on_release=self.save)
        cancel = FlatButton(text="Назад", bg=CARD_ALT)
        cancel.bind(on_release=lambda *_: setattr(self.app_ref.sm, "current", "home"))
        root.add_widget(save)
        root.add_widget(cancel)
        self.add_widget(root)

    def make_input(self, hint, multiline=False, height=dp(58), input_filter=None):
        field = TextInput(
            hint_text=hint,
            multiline=multiline,
            input_filter=input_filter,
            size_hint_y=None,
            height=height,
            background_normal="",
            background_active="",
            background_color=CARD,
            foreground_color=TEXT,
            hint_text_color=MUTED,
            cursor_color=PURPLE,
            padding=[dp(14), dp(14)],
            font_size="15sp",
        )
        return field

    def save(self, *_):
        title = self.title_input.text.strip()
        desc = self.desc_input.text.strip()
        category = self.category_input.text.strip() or "Личное"
        rarity = self.rarity_input.text.strip().capitalize() or "Обычная"
        allowed = ["Обычная", "Редкая", "Эпическая", "Легендарная"]
        if rarity not in allowed:
            rarity = "Обычная"
        try:
            xp = max(10, min(1000, int(self.xp_input.text or "50")))
        except ValueError:
            xp = 50

        if not title or not desc:
            Popup(
                title="Не хватает данных",
                content=txt("Заполни название и описание.", 16, TEXT, halign="center"),
                size_hint=(0.82, None),
                height=dp(200),
            ).open()
            return

        self.app_ref.db.add_achievement(title, desc, category, xp, rarity)
        for field in (
            self.title_input, self.desc_input, self.category_input,
            self.xp_input, self.rarity_input
        ):
            field.text = ""
        self.app_ref.sm.current = "home"


class LifeQuestApp(App):
    def build(self):
        Window.clearcolor = BG
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass

        data_dir = Path(self.user_data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db = LifeDB(str(data_dir / "lifequest.db"))

        self.sm = ScreenManager()
        self.sm.add_widget(HomeScreen(self, name="home"))
        self.sm.add_widget(AddScreen(self, name="add"))
        return self.sm

    def open_add(self):
        self.sm.current = "add"

    def show_history(self):
        rows = self.db.list_achievements(completed=True)
        body = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(8), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        if not rows:
            body.add_widget(txt("Пока нет выполненных ачивок.", 16, MUTED, size_hint_y=None, height=dp(80)))
        for row in rows:
            body.add_widget(AchievementCard(row))
        scroll = ScrollView()
        scroll.add_widget(body)
        Popup(
            title="История достижений",
            content=scroll,
            size_hint=(0.92, 0.86),
        ).open()


if __name__ == "__main__":
    LifeQuestApp().run()
