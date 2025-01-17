import random
import time

from database.dbc.DbcDatabaseManager import DbcDatabaseManager
from database.dbc.DbcModels import SpellRadius
from game.world.managers.objects.spell.aura.AuraEffectHandler import PERIODIC_AURA_EFFECTS
from game.world.managers.objects.spell.EffectTargets import EffectTargets
from utils.constants.SpellCodes import SpellEffects


class SpellEffect:
    effect_type: SpellEffects
    die_sides: int
    base_dice: int
    dice_per_level: int
    real_points_per_level: int
    base_points: int
    implicit_target_a: int
    implicit_target_b: int
    radius_index: int
    aura_type: int
    aura_period: int
    amplitude: int
    chain_targets: int
    item_type: int
    misc_value: int
    trigger_spell_id: int

    caster_effective_level: int
    effect_index: int
    targets: EffectTargets
    radius_entry: SpellRadius

    # Duration and periodic timing info for auras applied by this effect
    applied_aura_duration = -1
    periodic_effect_ticks = []
    last_update_timestamp = -1

    def __init__(self, casting_spell, index):
        self.load_effect(casting_spell.spell_entry, index)

        self.caster_effective_level = casting_spell.caster_effective_level
        self.targets = EffectTargets(casting_spell, self)
        self.radius_entry = DbcDatabaseManager.spell_radius_get_by_id(self.radius_index) if self.radius_index else None

        self.casting_spell = casting_spell

        is_periodic = self.aura_type in PERIODIC_AURA_EFFECTS
        # Descriptions of periodic effects with a period of 0 either imply regeneration every 5s or say "per tick".
        self.aura_period = (self.aura_period if self.aura_period else 5000) if is_periodic else 0

    def update_effect_aura(self, timestamp):
        if self.applied_aura_duration == -1:
            return

        self.applied_aura_duration -= (timestamp - self.last_update_timestamp) * 1000
        self.last_update_timestamp = timestamp

    def remove_old_periodic_effect_ticks(self):
        while self.is_past_next_period():
            self.periodic_effect_ticks.pop()

    def is_past_next_period(self):
        # Also accept equal duration to properly handle last tick.
        return len(self.periodic_effect_ticks) > 0 and self.periodic_effect_ticks[-1] >= self.applied_aura_duration

    def generate_periodic_effect_ticks(self) -> list[int]:
        duration = self.casting_spell.get_duration()
        if self.aura_period == 0:
            return []
        period = self.aura_period
        tick_count = int(duration / self.aura_period)

        ticks = []
        for i in range(tick_count):
            ticks.append(period * i)
        return ticks

    def start_aura_duration(self, overwrite=False):
        if not self.casting_spell.duration_entry or (len(self.periodic_effect_ticks) > 0 and not overwrite):
            return
        self.applied_aura_duration = self.casting_spell.get_duration()
        self.last_update_timestamp = time.time()
        if self.is_periodic():
            self.periodic_effect_ticks = self.generate_periodic_effect_ticks()

    def is_periodic(self):
        return self.aura_period != 0

    def get_effect_points(self) -> int:
        rolled_points = random.randint(1, self.die_sides + self.dice_per_level) if self.die_sides != 0 else 0
        return self.base_points + int(self.real_points_per_level * self.caster_effective_level) + rolled_points

    def get_effect_simple_points(self) -> int:
        return self.base_points + self.base_dice

    def get_radius(self) -> float:
        if not self.radius_entry:
            return 0
        return min(self.radius_entry.RadiusMax, self.radius_entry.Radius + self.radius_entry.RadiusPerLevel * self.caster_effective_level)

    # noinspection PyUnusedLocal
    def load_effect(self, spell, index):
        self.effect_type = eval(f'spell.Effect_{index+1}')
        self.die_sides = eval(f'spell.EffectDieSides_{index+1}')
        self.base_dice = eval(f'spell.EffectBaseDice_{index+1}')
        self.dice_per_level = eval(f'spell.EffectDicePerLevel_{index+1}')
        self.real_points_per_level = eval(f'spell.EffectRealPointsPerLevel_{index+1}')
        self.base_points = eval(f'spell.EffectBasePoints_{index+1}')
        self.implicit_target_a = eval(f'spell.ImplicitTargetA_{index+1}')
        self.implicit_target_b = eval(f'spell.ImplicitTargetB_{index+1}')
        self.radius_index = eval(f'spell.EffectRadiusIndex_{index+1}')
        self.aura_type = eval(f'spell.EffectAura_{index+1}')
        self.aura_period = eval(f'spell.EffectAuraPeriod_{index+1}')
        self.amplitude = eval(f'spell.EffectAmplitude_{index+1}')
        self.chain_targets = eval(f'spell.EffectChainTargets_{index+1}')
        self.item_type = eval(f'spell.EffectItemType_{index+1}')
        self.misc_value = eval(f'spell.EffectMiscValue_{index+1}')
        self.trigger_spell_id = eval(f'spell.EffectTriggerSpell_{index+1}')

        self.effect_index = index
