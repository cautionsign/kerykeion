# -*- coding: utf-8 -*-
"""
    This is part of Kerykeion (C) 2025 Giacomo Battaglia
"""


import logging
import swisseph as swe
from typing import get_args

from kerykeion.settings.kerykeion_settings import get_settings
from kerykeion.aspects.synastry_aspects import SynastryAspects
from kerykeion.aspects.natal_aspects import NatalAspects
from kerykeion.astrological_subject import AstrologicalSubject
from kerykeion.kr_types import KerykeionException, ChartType, KerykeionPointModel, Sign, ActiveAspect
from kerykeion.kr_types import ChartTemplateDictionary
from kerykeion.kr_types.kr_models import AstrologicalSubjectModel, CompositeSubjectModel
from kerykeion.kr_types.settings_models import KerykeionSettingsCelestialPointModel, KerykeionSettingsModel
from kerykeion.kr_types.kr_literals import KerykeionChartTheme, KerykeionChartLanguage, AxialCusps, Planet
from kerykeion.charts.charts_utils import (
    draw_zodiac_slice,
    convert_latitude_coordinate_to_string,
    convert_longitude_coordinate_to_string,
    draw_aspect_line,
    draw_transit_ring_degree_steps,
    draw_degree_ring,
    draw_transit_ring,
    draw_first_circle,
    draw_second_circle,
    draw_third_circle,
    draw_aspect_grid,
    draw_houses_cusps_and_text_number,
    draw_transit_aspect_list,
    draw_transit_aspect_grid,
    calculate_moon_phase_chart_params,
    draw_house_grid,
    draw_planet_grid,
)
from kerykeion.charts.draw_planets import draw_planets # type: ignore
from kerykeion.utilities import get_houses_list, inline_css_variables_in_svg
from kerykeion.settings.config_constants import DEFAULT_ACTIVE_POINTS, DEFAULT_ACTIVE_ASPECTS
from pathlib import Path
from scour.scour import scourString
from string import Template
from typing import Union, List, Literal
from datetime import datetime

class KerykeionChartSVG:
    """
    KerykeionChartSVG generates astrological chart visualizations as SVG files.

    This class supports creating full chart SVGs, wheel-only SVGs, and aspect-grid-only SVGs
    for various chart types including Natal, ExternalNatal, Transit, Synastry, and Composite.
    Charts are rendered using XML templates and drawing utilities, with customizable themes,
    language, active points, and aspects.
    The rendered SVGs can be saved to a specified output directory or, by default, to the user's home directory.

    NOTE:
        The generated SVG files are optimized for web use, opening in browsers. If you want to
        use them in other applications, you might need to adjust the SVG settings or styles.

    Args:
        first_obj (AstrologicalSubject | AstrologicalSubjectModel | CompositeSubjectModel):
            The primary astrological subject for the chart.
        chart_type (ChartType, optional):
            The type of chart to generate ('Natal', 'ExternalNatal', 'Transit', 'Synastry', 'Composite').
            Defaults to 'Natal'.
        second_obj (AstrologicalSubject | AstrologicalSubjectModel, optional):
            The secondary subject for Transit or Synastry charts. Not required for Natal or Composite.
        new_output_directory (str | Path, optional):
            Directory to write generated SVG files. Defaults to the user's home directory.
        new_settings_file (Path | dict | KerykeionSettingsModel, optional):
            Path or settings object to override default chart configuration (colors, fonts, aspects).
        theme (KerykeionChartTheme, optional):
            CSS theme for the chart. If None, no default styles are applied. Defaults to 'classic'.
        double_chart_aspect_grid_type (Literal['list', 'table'], optional):
            Specifies rendering style for double-chart aspect grids. Defaults to 'list'.
        chart_language (KerykeionChartLanguage, optional):
            Language code for chart labels. Defaults to 'EN'.
        active_points (list[Planet | AxialCusps], optional):
            List of celestial points and angles to include. Defaults to DEFAULT_ACTIVE_POINTS.
            Example:
            ["Sun", "Moon", "Mercury", "Venus"]

        active_aspects (list[ActiveAspect], optional):
            List of aspects (name and orb) to calculate. Defaults to DEFAULT_ACTIVE_ASPECTS.
            Example:
            [
                {"name": "conjunction", "orb": 10},
                {"name": "opposition", "orb": 10},
                {"name": "trine", "orb": 8},
                {"name": "sextile", "orb": 6},
                {"name": "square", "orb": 5},
                {"name": "quintile", "orb": 1},
            ]

    Public Methods:
        makeTemplate(minify=False, remove_css_variables=False) -> str:
            Render the full chart SVG as a string without writing to disk. Use `minify=True`
            to remove whitespace and quotes, and `remove_css_variables=True` to embed CSS vars.

        makeSVG(minify=False, remove_css_variables=False) -> None:
            Generate and write the full chart SVG file to the output directory.
            Filenames follow the pattern:
            '{subject.name} - {chart_type} Chart.svg'.

        makeWheelOnlyTemplate(minify=False, remove_css_variables=False) -> str:
            Render only the chart wheel (no aspect grid) as an SVG string.

        makeWheelOnlySVG(minify=False, remove_css_variables=False) -> None:
            Generate and write the wheel-only SVG file:
            '{subject.name} - {chart_type} Chart - Wheel Only.svg'.

        makeAspectGridOnlyTemplate(minify=False, remove_css_variables=False) -> str:
            Render only the aspect grid as an SVG string.

        makeAspectGridOnlySVG(minify=False, remove_css_variables=False) -> None:
            Generate and write the aspect-grid-only SVG file:
            '{subject.name} - {chart_type} Chart - Aspect Grid Only.svg'.
    """

    # Constants
    _BASIC_CHART_VIEWBOX = "0 0 820 550.0"
    _WIDE_CHART_VIEWBOX = "0 0 1200 546.0"
    _TRANSIT_CHART_WITH_TABLE_VIWBOX = "0 0 960 546.0"

    _DEFAULT_HEIGHT = 550
    _DEFAULT_FULL_WIDTH = 1200
    _DEFAULT_NATAL_WIDTH = 820
    _DEFAULT_FULL_WIDTH_WITH_TABLE = 960
    _PLANET_IN_ZODIAC_EXTRA_POINTS = 10

    # Set at init
    first_obj: Union[AstrologicalSubject, AstrologicalSubjectModel]
    second_obj: Union[AstrologicalSubject, AstrologicalSubjectModel, None]
    chart_type: ChartType
    new_output_directory: Union[Path, None]
    new_settings_file: Union[Path, None, KerykeionSettingsModel, dict]
    output_directory: Path
    new_settings_file: Union[Path, None, KerykeionSettingsModel, dict]
    theme: Union[KerykeionChartTheme, None]
    double_chart_aspect_grid_type: Literal["list", "table"]
    chart_language: KerykeionChartLanguage
    active_points: List[Union[Planet, AxialCusps]]
    active_aspects: List[ActiveAspect]

    # Internal properties
    fire: float
    earth: float
    air: float
    water: float
    first_circle_radius: float
    second_circle_radius: float
    third_circle_radius: float
    width: Union[float, int]
    language_settings: dict
    chart_colors_settings: dict
    planets_settings: dict
    aspects_settings: dict
    user: Union[AstrologicalSubject, AstrologicalSubjectModel, CompositeSubjectModel]
    available_planets_setting: List[KerykeionSettingsCelestialPointModel]
    height: float
    location: str
    geolat: float
    geolon: float
    template: str

    def __init__(
        self,
        first_obj: Union[AstrologicalSubject, AstrologicalSubjectModel, CompositeSubjectModel],
        chart_type: ChartType = "Natal",
        second_obj: Union[AstrologicalSubject, AstrologicalSubjectModel, None] = None,
        new_output_directory: Union[str, None] = None,
        new_settings_file: Union[Path, None, KerykeionSettingsModel, dict] = None,
        theme: Union[KerykeionChartTheme, None] = "classic",
        double_chart_aspect_grid_type: Literal["list", "table"] = "list",
        chart_language: KerykeionChartLanguage = "EN",
        active_points: List[Union[Planet, AxialCusps]] = DEFAULT_ACTIVE_POINTS,
    active_aspects: List[ActiveAspect] = DEFAULT_ACTIVE_ASPECTS,
    ):
        """
        Initialize the chart generator with subject data and configuration options.

        Args:
            first_obj (AstrologicalSubject, AstrologicalSubjectModel, or CompositeSubjectModel):
                Primary astrological subject instance.
            chart_type (ChartType, optional):
                Type of chart to generate (e.g., 'Natal', 'Transit').
            second_obj (AstrologicalSubject or AstrologicalSubjectModel, optional):
                Secondary subject for Transit or Synastry charts.
            new_output_directory (str or Path, optional):
                Base directory to save generated SVG files.
            new_settings_file (Path, dict, or KerykeionSettingsModel, optional):
                Custom settings source for chart colors, fonts, and aspects.
            theme (KerykeionChartTheme or None, optional):
                CSS theme to apply; None for default styling.
            double_chart_aspect_grid_type (Literal['list','table'], optional):
                Layout style for double-chart aspect grids ('list' or 'table').
            chart_language (KerykeionChartLanguage, optional):
                Language code for chart labels (e.g., 'EN', 'IT').
            active_points (List[Planet or AxialCusps], optional):
                Celestial points to include in the chart visualization.
            active_aspects (List[ActiveAspect], optional):
                Aspects to calculate, each defined by name and orb.
        """
        home_directory = Path.home()
        self.new_settings_file = new_settings_file
        self.chart_language = chart_language
        self.active_points = active_points
        self.active_aspects = active_aspects

        if new_output_directory:
            self.output_directory = Path(new_output_directory)
        else:
            self.output_directory = home_directory

        self.parse_json_settings(new_settings_file)
        self.chart_type = chart_type

        # Kerykeion instance
        self.user = first_obj

        self.available_planets_setting = []
        for body in self.planets_settings:
            if body["name"] not in active_points:
                continue
            else:
                body["is_active"] = True

            self.available_planets_setting.append(body)

        # Available bodies
        available_celestial_points_names = []
        for body in self.available_planets_setting:
            available_celestial_points_names.append(body["name"].lower())

        self.available_kerykeion_celestial_points: list[KerykeionPointModel] = []
        for body in available_celestial_points_names:
            self.available_kerykeion_celestial_points.append(self.user.get(body))

        # Makes the sign number list.
        if self.chart_type == "Natal" or self.chart_type == "ExternalNatal":
            natal_aspects_instance = NatalAspects(
                self.user, new_settings_file=self.new_settings_file,
                active_points=active_points,
                active_aspects=active_aspects,
            )
            self.aspects_list = natal_aspects_instance.relevant_aspects

        elif self.chart_type == "Transit" or self.chart_type == "Synastry":
            if not second_obj:
                raise KerykeionException("Second object is required for Transit or Synastry charts.")

            # Kerykeion instance
            self.t_user = second_obj

            # Aspects
            if self.chart_type == "Transit":
                synastry_aspects_instance = SynastryAspects(
                    self.t_user,
                    self.user,
                    new_settings_file=self.new_settings_file,
                    active_points=active_points,
                    active_aspects=active_aspects,
                )

            else:
                synastry_aspects_instance = SynastryAspects(
                    self.user,
                    self.t_user,
                    new_settings_file=self.new_settings_file,
                    active_points=active_points,
                    active_aspects=active_aspects,
                )

            self.aspects_list = synastry_aspects_instance.relevant_aspects

            self.t_available_kerykeion_celestial_points = []
            for body in available_celestial_points_names:
                self.t_available_kerykeion_celestial_points.append(self.t_user.get(body))

        elif self.chart_type == "Composite":
            if not isinstance(first_obj, CompositeSubjectModel):
                raise KerykeionException("First object must be a CompositeSubjectModel instance.")

            self.aspects_list = NatalAspects(self.user, new_settings_file=self.new_settings_file, active_points=active_points).relevant_aspects

        # Double chart aspect grid type
        self.double_chart_aspect_grid_type = double_chart_aspect_grid_type

        # screen size
        self.height = self._DEFAULT_HEIGHT
        if self.chart_type == "Synastry" or self.chart_type == "Transit":
            self.width = self._DEFAULT_FULL_WIDTH
        elif self.double_chart_aspect_grid_type == "table" and self.chart_type == "Transit":
            self.width = self._DEFAULT_FULL_WIDTH_WITH_TABLE
        else:
            self.width = self._DEFAULT_NATAL_WIDTH

        if self.chart_type in ["Natal", "ExternalNatal", "Synastry"]:
            self.location = self.user.city
            self.geolat = self.user.lat
            self.geolon =  self.user.lng

        elif self.chart_type == "Composite":
            self.location = ""
            self.geolat = (self.user.first_subject.lat + self.user.second_subject.lat) / 2
            self.geolon = (self.user.first_subject.lng + self.user.second_subject.lng) / 2

        elif self.chart_type in ["Transit"]:
            self.location = self.t_user.city
            self.geolat = self.t_user.lat
            self.geolon = self.t_user.lng
            self.t_name = self.language_settings["transit_name"]

        # Default radius for the chart
        self.main_radius = 240

        # Set circle radii based on chart type
        if self.chart_type == "ExternalNatal":
            self.first_circle_radius, self.second_circle_radius, self.third_circle_radius = 56, 92, 112
        else:
            self.first_circle_radius, self.second_circle_radius, self.third_circle_radius = 0, 36, 120

        # Initialize element points
        self.fire = 0.0
        self.earth = 0.0
        self.air = 0.0
        self.water = 0.0

        # Calculate element points from planets
        self._calculate_elements_points_from_planets()

        # Set up theme
        if theme not in get_args(KerykeionChartTheme) and theme is not None:
            raise KerykeionException(f"Theme {theme} is not available. Set None for default theme.")

        self.set_up_theme(theme)

    def set_up_theme(self, theme: Union[KerykeionChartTheme, None] = None) -> None:
        """
        Load and apply a CSS theme for the chart visualization.

        Args:
            theme (KerykeionChartTheme or None): Name of the theme to apply. If None, no CSS is applied.
        """
        if theme is None:
            self.color_style_tag = ""
            return

        theme_dir = Path(__file__).parent / "themes"

        with open(theme_dir / f"{theme}.css", "r") as f:
            self.color_style_tag = f.read()

    def set_output_directory(self, dir_path: Path) -> None:
        """
        Set the directory where generated SVG files will be saved.

        Args:
            dir_path (Path): Target directory for SVG output.
        """
        self.output_directory = dir_path
        logging.info(f"Output direcotry set to: {self.output_directory}")

    def parse_json_settings(self, settings_file_or_dict: Union[Path, dict, KerykeionSettingsModel, None]) -> None:
        """
        Load and parse chart configuration settings.

        Args:
            settings_file_or_dict (Path, dict, or KerykeionSettingsModel):
                Source for custom chart settings.
        """
        settings = get_settings(settings_file_or_dict)

        self.language_settings = settings["language_settings"][self.chart_language]
        self.chart_colors_settings = settings["chart_colors"]
        self.planets_settings = settings["celestial_points"]
        self.aspects_settings = settings["aspects"]

    def _draw_zodiac_circle_slices(self, r):
        """
        Draw zodiac circle slices for each sign.

        Args:
            r (float): Outer radius of the zodiac ring.

        Returns:
            str: Concatenated SVG elements for zodiac slices.
        """
        sings = get_args(Sign)
        output = ""
        for i, sing in enumerate(sings):
            output += draw_zodiac_slice(
                c1=self.first_circle_radius,
                chart_type=self.chart_type,
                seventh_house_degree_ut=self.user.seventh_house.abs_pos,
                num=i,
                r=r,
                style=f'fill:{self.chart_colors_settings[f"zodiac_bg_{i}"]}; fill-opacity: 0.5;',
                type=sing,
            )

        return output

    def _calculate_elements_points_from_planets(self):
        """
        Compute elemental point totals based on active planetary positions.

        Iterates over each active planet to determine its zodiac element and adds extra points
        if the planet is in a related sign. Updates self.fire, self.earth, self.air, and self.water.

        Returns:
            None
        """

        ZODIAC = (
            {"name": "Ari", "element": "fire"},
            {"name": "Tau", "element": "earth"},
            {"name": "Gem", "element": "air"},
            {"name": "Can", "element": "water"},
            {"name": "Leo", "element": "fire"},
            {"name": "Vir", "element": "earth"},
            {"name": "Lib", "element": "air"},
            {"name": "Sco", "element": "water"},
            {"name": "Sag", "element": "fire"},
            {"name": "Cap", "element": "earth"},
            {"name": "Aqu", "element": "air"},
            {"name": "Pis", "element": "water"},
        )

        # Available bodies
        available_celestial_points_names = []
        for body in self.available_planets_setting:
            available_celestial_points_names.append(body["name"].lower())

        # Make list of the points sign
        points_sign = []
        for planet in available_celestial_points_names:
            points_sign.append(self.user.get(planet).sign_num)

        for i in range(len(self.available_planets_setting)):
            # element: get extra points if planet is in own zodiac sign.
            related_zodiac_signs = self.available_planets_setting[i]["related_zodiac_signs"]
            cz = points_sign[i]
            extra_points = 0
            if related_zodiac_signs != []:
                for e in range(len(related_zodiac_signs)):
                    if int(related_zodiac_signs[e]) == int(cz):
                        extra_points = self._PLANET_IN_ZODIAC_EXTRA_POINTS

            ele = ZODIAC[points_sign[i]]["element"]
            if ele == "fire":
                self.fire = self.fire + self.available_planets_setting[i]["element_points"] + extra_points

            elif ele == "earth":
                self.earth = self.earth + self.available_planets_setting[i]["element_points"] + extra_points

            elif ele == "air":
                self.air = self.air + self.available_planets_setting[i]["element_points"] + extra_points

            elif ele == "water":
                self.water = self.water + self.available_planets_setting[i]["element_points"] + extra_points

    def _draw_all_aspects_lines(self, r, ar):
        """
        Render SVG lines for all aspects in the chart.

        Args:
            r (float): Radius at which aspect lines originate.
            ar (float): Radius at which aspect lines terminate.

        Returns:
            str: SVG markup for all aspect lines.
        """
        out = ""
        for aspect in self.aspects_list:
            aspect_name = aspect["aspect"]
            aspect_color = next((a["color"] for a in self.aspects_settings if a["name"] == aspect_name), None)
            if aspect_color:
                out += draw_aspect_line(
                    r=r,
                    ar=ar,
                    aspect=aspect,
                    color=aspect_color,
                    seventh_house_degree_ut=self.user.seventh_house.abs_pos
                )
        return out

    def _draw_all_transit_aspects_lines(self, r, ar):
        """
        Render SVG lines for all transit aspects in the chart.

        Args:
            r (float): Radius at which transit aspect lines originate.
            ar (float): Radius at which transit aspect lines terminate.

        Returns:
            str: SVG markup for all transit aspect lines.
        """
        out = ""
        for aspect in self.aspects_list:
            aspect_name = aspect["aspect"]
            aspect_color = next((a["color"] for a in self.aspects_settings if a["name"] == aspect_name), None)
            if aspect_color:
                out += draw_aspect_line(
                    r=r,
                    ar=ar,
                    aspect=aspect,
                    color=aspect_color,
                    seventh_house_degree_ut=self.user.seventh_house.abs_pos
                )
        return out

    def _create_template_dictionary(self) -> ChartTemplateDictionary:
        """
        Assemble chart data and rendering instructions into a template dictionary.

        Gathers styling, dimensions, and SVG fragments for chart components based on
        chart type and subjects.

        Returns:
            ChartTemplateDictionary: Populated structure of template variables.
        """
        # Initialize template dictionary
        template_dict: dict = {}

        # Set the color style tag
        template_dict["color_style_tag"] = self.color_style_tag

        # Set chart dimensions
        template_dict["chart_height"] = self.height
        template_dict["chart_width"] = self.width

        # Set viewbox based on chart type
        if self.chart_type in ["Natal", "ExternalNatal", "Composite"]:
            template_dict['viewbox'] = self._BASIC_CHART_VIEWBOX
        elif self.double_chart_aspect_grid_type == "table" and self.chart_type == "Transit":
            template_dict['viewbox'] = self._TRANSIT_CHART_WITH_TABLE_VIWBOX
        else:
            template_dict['viewbox'] = self._WIDE_CHART_VIEWBOX

        # Generate rings and circles based on chart type
        if self.chart_type in ["Transit", "Synastry"]:
            template_dict["transitRing"] = draw_transit_ring(self.main_radius, self.chart_colors_settings["paper_1"], self.chart_colors_settings["zodiac_transit_ring_3"])
            template_dict["degreeRing"] = draw_transit_ring_degree_steps(self.main_radius, self.user.seventh_house.abs_pos)
            template_dict["first_circle"] = draw_first_circle(self.main_radius, self.chart_colors_settings["zodiac_transit_ring_2"], self.chart_type)
            template_dict["second_circle"] = draw_second_circle(self.main_radius, self.chart_colors_settings['zodiac_transit_ring_1'], self.chart_colors_settings['paper_1'], self.chart_type)
            template_dict['third_circle'] = draw_third_circle(self.main_radius, self.chart_colors_settings['zodiac_transit_ring_0'], self.chart_colors_settings['paper_1'], self.chart_type, self.third_circle_radius)

            if self.double_chart_aspect_grid_type == "list":
                title = ""
                if self.chart_type == "Synastry":
                    title = self.language_settings.get("couple_aspects", "Couple Aspects")
                else:
                    title = self.language_settings.get("transit_aspects", "Transit Aspects")

                template_dict["makeAspectGrid"] = draw_transit_aspect_list(title, self.aspects_list, self.planets_settings, self.aspects_settings)
            else:
                template_dict["makeAspectGrid"] = draw_transit_aspect_grid(self.chart_colors_settings['paper_0'], self.available_planets_setting, self.aspects_list, 550, 450)

            template_dict["makeAspects"] = self._draw_all_transit_aspects_lines(self.main_radius, self.main_radius - 160)
        else:
            template_dict["transitRing"] = ""
            template_dict["degreeRing"] = draw_degree_ring(self.main_radius, self.first_circle_radius, self.user.seventh_house.abs_pos, self.chart_colors_settings["paper_0"])
            template_dict['first_circle'] = draw_first_circle(self.main_radius, self.chart_colors_settings["zodiac_radix_ring_2"], self.chart_type, self.first_circle_radius)
            template_dict["second_circle"] = draw_second_circle(self.main_radius, self.chart_colors_settings["zodiac_radix_ring_1"], self.chart_colors_settings["paper_1"], self.chart_type, self.second_circle_radius)
            template_dict['third_circle'] = draw_third_circle(self.main_radius, self.chart_colors_settings["zodiac_radix_ring_0"], self.chart_colors_settings["paper_1"], self.chart_type, self.third_circle_radius)
            template_dict["makeAspectGrid"] = draw_aspect_grid(self.chart_colors_settings['paper_0'], self.available_planets_setting, self.aspects_list)

            template_dict["makeAspects"] = self._draw_all_aspects_lines(self.main_radius, self.main_radius - self.third_circle_radius)

        # Set chart title
        if self.chart_type == "Synastry":
            template_dict["stringTitle"] = f"{self.user.name} {self.language_settings['and_word']} {self.t_user.name}"
        elif self.chart_type == "Transit":
            template_dict["stringTitle"] = f"{self.language_settings['transits']} {self.t_user.day}/{self.t_user.month}/{self.t_user.year}"
        elif self.chart_type in ["Natal", "ExternalNatal"]:
            template_dict["stringTitle"] = self.user.name
        elif self.chart_type == "Composite":
            template_dict["stringTitle"] = f"{self.user.first_subject.name} {self.language_settings['and_word']} {self.user.second_subject.name}"

        # Zodiac Type Info
        if self.user.zodiac_type == 'Tropic':
            zodiac_info = f"{self.language_settings.get('zodiac', 'Zodiac')}: {self.language_settings.get('tropical', 'Tropical')}"
        else:
            mode_const = "SIDM_" + self.user.sidereal_mode # type: ignore
            mode_name = swe.get_ayanamsa_name(getattr(swe, mode_const))
            zodiac_info = f"{self.language_settings.get('ayanamsa', 'Ayanamsa')}: {mode_name}"

        template_dict["bottom_left_0"] = f"{self.language_settings.get('houses_system_' + self.user.houses_system_identifier, self.user.houses_system_name)} {self.language_settings.get('houses', 'Houses')}"
        template_dict["bottom_left_1"] = zodiac_info

        if self.chart_type in ["Natal", "ExternalNatal", "Synastry"]:
            template_dict["bottom_left_2"] = f'{self.language_settings.get("lunar_phase", "Lunar Phase")} {self.language_settings.get("day", "Day").lower()}: {self.user.lunar_phase.get("moon_phase", "")}'
            template_dict["bottom_left_3"] = f'{self.language_settings.get("lunar_phase", "Lunar Phase")}: {self.language_settings.get(self.user.lunar_phase.moon_phase_name.lower().replace(" ", "_"), self.user.lunar_phase.moon_phase_name)}'
            template_dict["bottom_left_4"] = f'{self.language_settings.get(self.user.perspective_type.lower().replace(" ", "_"), self.user.perspective_type)}'
        elif self.chart_type == "Transit":
            template_dict["bottom_left_2"] = f'{self.language_settings.get("lunar_phase", "Lunar Phase")}: {self.language_settings.get("day", "Day")} {self.t_user.lunar_phase.get("moon_phase", "")}'
            template_dict["bottom_left_3"] = f'{self.language_settings.get("lunar_phase", "Lunar Phase")}: {self.t_user.lunar_phase.moon_phase_name}'
            template_dict["bottom_left_4"] = f'{self.language_settings.get(self.t_user.perspective_type.lower().replace(" ", "_"), self.t_user.perspective_type)}'
        elif self.chart_type == "Composite":
            template_dict["bottom_left_2"] = f'{self.user.first_subject.perspective_type}'
            template_dict["bottom_left_3"] = f'{self.language_settings.get("composite_chart", "Composite Chart")} - {self.language_settings.get("midpoints", "Midpoints")}'
            template_dict["bottom_left_4"] = ""

        # Draw moon phase
        moon_phase_dict = calculate_moon_phase_chart_params(
            self.user.lunar_phase["degrees_between_s_m"],
            self.geolat
        )

        template_dict["lunar_phase_rotate"] = moon_phase_dict["lunar_phase_rotate"]
        template_dict["lunar_phase_circle_center_x"] = moon_phase_dict["circle_center_x"]
        template_dict["lunar_phase_circle_radius"] = moon_phase_dict["circle_radius"]

        if self.chart_type == "Composite":
            template_dict["top_left_1"] = f"{datetime.fromisoformat(self.user.first_subject.iso_formatted_local_datetime).strftime('%Y-%m-%d %H:%M')}"
        # Set location string
        elif len(self.location) > 35:
            split_location = self.location.split(",")
            if len(split_location) > 1:
                template_dict["top_left_1"] = split_location[0] + ", " + split_location[-1]
                if len(template_dict["top_left_1"]) > 35:
                    template_dict["top_left_1"] = template_dict["top_left_1"][:35] + "..."
            else:
                template_dict["top_left_1"] = self.location[:35] + "..."
        else:
            template_dict["top_left_1"] = self.location

        # Set chart name
        if self.chart_type in ["Synastry", "Transit"]:
            template_dict["top_left_0"] = f"{self.user.name}:"
        elif self.chart_type in ["Natal", "ExternalNatal"]:
            template_dict["top_left_0"] = f'{self.language_settings["info"]}:'
        elif self.chart_type == "Composite":
            template_dict["top_left_0"] = f'{self.user.first_subject.name}'

        # Set additional information for Synastry chart type
        if self.chart_type == "Synastry":
            template_dict["top_left_3"] = f"{self.t_user.name}: "
            template_dict["top_left_4"] = self.t_user.city
            template_dict["top_left_5"] = f"{self.t_user.year}-{self.t_user.month}-{self.t_user.day} {self.t_user.hour:02d}:{self.t_user.minute:02d}"
        elif self.chart_type == "Composite":
            template_dict["top_left_3"] = self.user.second_subject.name
            template_dict["top_left_4"] = f"{datetime.fromisoformat(self.user.second_subject.iso_formatted_local_datetime).strftime('%Y-%m-%d %H:%M')}"
            latitude_string = convert_latitude_coordinate_to_string(self.user.second_subject.lat, self.language_settings['north_letter'], self.language_settings['south_letter'])
            longitude_string = convert_longitude_coordinate_to_string(self.user.second_subject.lng, self.language_settings['east_letter'], self.language_settings['west_letter'])
            template_dict["top_left_5"] = f"{latitude_string} / {longitude_string}"
        else:
            latitude_string = convert_latitude_coordinate_to_string(self.geolat, self.language_settings['north'], self.language_settings['south'])
            longitude_string = convert_longitude_coordinate_to_string(self.geolon, self.language_settings['east'], self.language_settings['west'])
            template_dict["top_left_3"] = f"{self.language_settings['latitude']}: {latitude_string}"
            template_dict["top_left_4"] = f"{self.language_settings['longitude']}: {longitude_string}"
            template_dict["top_left_5"] = f"{self.language_settings['type']}: {self.language_settings.get(self.chart_type, self.chart_type)}"


        # Set paper colors
        template_dict["paper_color_0"] = self.chart_colors_settings["paper_0"]
        template_dict["paper_color_1"] = self.chart_colors_settings["paper_1"]

        # Set planet colors
        for planet in self.planets_settings:
            planet_id = planet["id"]
            template_dict[f"planets_color_{planet_id}"] = planet["color"] # type: ignore

        # Set zodiac colors
        for i in range(12):
            template_dict[f"zodiac_color_{i}"] = self.chart_colors_settings[f"zodiac_icon_{i}"] # type: ignore

        # Set orb colors
        for aspect in self.aspects_settings:
            template_dict[f"orb_color_{aspect['degree']}"] = aspect['color'] # type: ignore

        # Drawing functions
        template_dict["makeZodiac"] = self._draw_zodiac_circle_slices(self.main_radius)

        first_subject_houses_list = get_houses_list(self.user)

        # Draw houses grid and cusps
        if self.chart_type in ["Transit", "Synastry"]:
            second_subject_houses_list = get_houses_list(self.t_user)

            template_dict["makeHousesGrid"] = draw_house_grid(
                main_subject_houses_list=first_subject_houses_list,
                secondary_subject_houses_list=second_subject_houses_list,
                chart_type=self.chart_type,
                text_color=self.chart_colors_settings["paper_0"],
                house_cusp_generale_name_label=self.language_settings["cusp"]
            )

            template_dict["makeHouses"] = draw_houses_cusps_and_text_number(
                r=self.main_radius,
                first_subject_houses_list=first_subject_houses_list,
                standard_house_cusp_color=self.chart_colors_settings["houses_radix_line"],
                first_house_color=self.planets_settings[12]["color"],
                tenth_house_color=self.planets_settings[13]["color"],
                seventh_house_color=self.planets_settings[14]["color"],
                fourth_house_color=self.planets_settings[15]["color"],
                c1=self.first_circle_radius,
                c3=self.third_circle_radius,
                chart_type=self.chart_type,
                second_subject_houses_list=second_subject_houses_list,
                transit_house_cusp_color=self.chart_colors_settings["houses_transit_line"],
            )

        else:
            template_dict["makeHousesGrid"] = draw_house_grid(
                main_subject_houses_list=first_subject_houses_list,
                chart_type=self.chart_type,
                text_color=self.chart_colors_settings["paper_0"],
                house_cusp_generale_name_label=self.language_settings["cusp"]
            )

            template_dict["makeHouses"] = draw_houses_cusps_and_text_number(
                r=self.main_radius,
                first_subject_houses_list=first_subject_houses_list,
                standard_house_cusp_color=self.chart_colors_settings["houses_radix_line"],
                first_house_color=self.planets_settings[12]["color"],
                tenth_house_color=self.planets_settings[13]["color"],
                seventh_house_color=self.planets_settings[14]["color"],
                fourth_house_color=self.planets_settings[15]["color"],
                c1=self.first_circle_radius,
                c3=self.third_circle_radius,
                chart_type=self.chart_type,
            )

        # Draw planets
        if self.chart_type in ["Transit", "Synastry"]:
            template_dict["makePlanets"] = draw_planets(
                available_kerykeion_celestial_points=self.available_kerykeion_celestial_points,
                available_planets_setting=self.available_planets_setting,
                second_subject_available_kerykeion_celestial_points=self.t_available_kerykeion_celestial_points,
                radius=self.main_radius,
                main_subject_first_house_degree_ut=self.user.first_house.abs_pos,
                main_subject_seventh_house_degree_ut=self.user.seventh_house.abs_pos,
                chart_type=self.chart_type,
                third_circle_radius=self.third_circle_radius,
            )
        else:
            template_dict["makePlanets"] = draw_planets(
                available_planets_setting=self.available_planets_setting,
                chart_type=self.chart_type,
                radius=self.main_radius,
                available_kerykeion_celestial_points=self.available_kerykeion_celestial_points,
                third_circle_radius=self.third_circle_radius,
                main_subject_first_house_degree_ut=self.user.first_house.abs_pos,
                main_subject_seventh_house_degree_ut=self.user.seventh_house.abs_pos
            )

        # Draw elements percentages
        total = self.fire + self.water + self.earth + self.air

        fire_percentage = int(round(100 * self.fire / total))
        earth_percentage = int(round(100 * self.earth / total))
        air_percentage = int(round(100 * self.air / total))
        water_percentage = int(round(100 * self.water / total))

        template_dict["fire_string"] = f"{self.language_settings['fire']} {fire_percentage}%"
        template_dict["earth_string"] = f"{self.language_settings['earth']} {earth_percentage}%"
        template_dict["air_string"] = f"{self.language_settings['air']} {air_percentage}%"
        template_dict["water_string"] = f"{self.language_settings['water']} {water_percentage}%"

        # Draw planet grid
        if self.chart_type in ["Transit", "Synastry"]:
            if self.chart_type == "Transit":
                second_subject_table_name = self.language_settings["transit_name"]
            else:
                second_subject_table_name = self.t_user.name

            template_dict["makePlanetGrid"] = draw_planet_grid(
                planets_and_houses_grid_title=self.language_settings["planets_and_house"],
                subject_name=self.user.name,
                available_kerykeion_celestial_points=self.available_kerykeion_celestial_points,
                chart_type=self.chart_type,
                text_color=self.chart_colors_settings["paper_0"],
                celestial_point_language=self.language_settings["celestial_points"],
                second_subject_name=second_subject_table_name,
                second_subject_available_kerykeion_celestial_points=self.t_available_kerykeion_celestial_points,
            )
        else:
            if self.chart_type == "Composite":
                subject_name = f"{self.user.first_subject.name} {self.language_settings['and_word']} {self.user.second_subject.name}"
            else:
                subject_name = self.user.name

            template_dict["makePlanetGrid"] = draw_planet_grid(
                planets_and_houses_grid_title=self.language_settings["planets_and_house"],
                subject_name=subject_name,
                available_kerykeion_celestial_points=self.available_kerykeion_celestial_points,
                chart_type=self.chart_type,
                text_color=self.chart_colors_settings["paper_0"],
                celestial_point_language=self.language_settings["celestial_points"],
            )

        # Set date time string
        if self.chart_type in ["Composite"]:
            # First Subject Latitude and Longitude
            latitude = convert_latitude_coordinate_to_string(self.user.first_subject.lat, self.language_settings["north_letter"], self.language_settings["south_letter"])
            longitude = convert_longitude_coordinate_to_string(self.user.first_subject.lng, self.language_settings["east_letter"], self.language_settings["west_letter"])
            template_dict["top_left_2"] = f"{latitude} {longitude}"
        else:
            dt = datetime.fromisoformat(self.user.iso_formatted_local_datetime)
            custom_format = dt.strftime('%Y-%m-%d %H:%M [%z]')
            custom_format = custom_format[:-3] + ':' + custom_format[-3:]
            template_dict["top_left_2"] = f"{custom_format}"

        return ChartTemplateDictionary(**template_dict)

    def makeTemplate(self, minify: bool = False, remove_css_variables = False) -> str:
        """
        Render the full chart SVG as a string.

        Reads the XML template, substitutes variables, and optionally inlines CSS
        variables and minifies the output.

        Args:
            minify (bool): Remove whitespace and quotes for compactness.
            remove_css_variables (bool): Embed CSS variable definitions.

        Returns:
            str: SVG markup as a string.
        """
        td = self._create_template_dictionary()

        DATA_DIR = Path(__file__).parent
        xml_svg = DATA_DIR / "templates" / "chart.xml"

        # read template
        with open(xml_svg, "r", encoding="utf-8", errors="ignore") as f:
            template = Template(f.read()).substitute(td)

        # return filename

        logging.debug(f"Template dictionary keys: {td.keys()}")

        self._create_template_dictionary()

        if remove_css_variables:
            template = inline_css_variables_in_svg(template)

        if minify:
            template = scourString(template).replace('"', "'").replace("\n", "").replace("\t","").replace("    ", "").replace("  ", "")

        else:
            template = template.replace('"', "'")

        return template

    def makeSVG(self, minify: bool = False, remove_css_variables = False):
        """
        Generate and save the full chart SVG to disk.

        Calls makeTemplate to render the SVG, then writes a file named
        "{subject.name} - {chart_type} Chart.svg" in the output directory.

        Args:
            minify (bool): Pass-through to makeTemplate for compact output.
            remove_css_variables (bool): Pass-through to makeTemplate to embed CSS variables.

        Returns:
            None
        """

        self.template = self.makeTemplate(minify, remove_css_variables)

        chartname = self.output_directory / f"{self.user.name} - {self.chart_type} Chart.svg"

        with open(chartname, "w", encoding="utf-8", errors="ignore") as output_file:
            output_file.write(self.template)

        print(f"SVG Generated Correctly in: {chartname}")

    def makeWheelOnlyTemplate(self, minify: bool = False, remove_css_variables = False):
        """
        Render the wheel-only chart SVG as a string.

        Reads the wheel-only XML template, substitutes chart data, and applies optional
        CSS inlining and minification.

        Args:
            minify (bool): Remove whitespace and quotes for compactness.
            remove_css_variables (bool): Embed CSS variable definitions.

        Returns:
            str: SVG markup for the chart wheel only.
        """

        with open(Path(__file__).parent / "templates" / "wheel_only.xml", "r", encoding="utf-8", errors="ignore") as f:
            template = f.read()

        template_dict = self._create_template_dictionary()
        template = Template(template).substitute(template_dict)

        if remove_css_variables:
            template = inline_css_variables_in_svg(template)

        if minify:
            template = scourString(template).replace('"', "'").replace("\n", "").replace("\t","").replace("    ", "").replace("  ", "")

        else:
            template = template.replace('"', "'")

        return template

    def makeWheelOnlySVG(self, minify: bool = False, remove_css_variables = False):
        """
        Generate and save wheel-only chart SVG to disk.

        Calls makeWheelOnlyTemplate and writes a file named
        "{subject.name} - {chart_type} Chart - Wheel Only.svg" in the output directory.

        Args:
            minify (bool): Pass-through to makeWheelOnlyTemplate for compact output.
            remove_css_variables (bool): Pass-through to makeWheelOnlyTemplate to embed CSS variables.

        Returns:
            None
        """

        template = self.makeWheelOnlyTemplate(minify, remove_css_variables)
        chartname = self.output_directory / f"{self.user.name} - {self.chart_type} Chart - Wheel Only.svg"

        with open(chartname, "w", encoding="utf-8", errors="ignore") as output_file:
            output_file.write(template)

        print(f"SVG Generated Correctly in: {chartname}")

    def makeAspectGridOnlyTemplate(self, minify: bool = False, remove_css_variables = False):
        """
        Render the aspect-grid-only chart SVG as a string.

        Reads the aspect-grid XML template, generates the aspect grid based on chart type,
        and applies optional CSS inlining and minification.

        Args:
            minify (bool): Remove whitespace and quotes for compactness.
            remove_css_variables (bool): Embed CSS variable definitions.

        Returns:
            str: SVG markup for the aspect grid only.
        """

        with open(Path(__file__).parent / "templates" / "aspect_grid_only.xml", "r", encoding="utf-8", errors="ignore") as f:
            template = f.read()

        template_dict = self._create_template_dictionary()

        if self.chart_type in ["Transit", "Synastry"]:
            aspects_grid = draw_transit_aspect_grid(self.chart_colors_settings['paper_0'], self.available_planets_setting, self.aspects_list)
        else:
            aspects_grid = draw_aspect_grid(self.chart_colors_settings['paper_0'], self.available_planets_setting, self.aspects_list, x_start=50, y_start=250)

        template = Template(template).substitute({**template_dict, "makeAspectGrid": aspects_grid})

        if remove_css_variables:
            template = inline_css_variables_in_svg(template)

        if minify:
            template = scourString(template).replace('"', "'").replace("\n", "").replace("\t","").replace("    ", "").replace("  ", "")

        else:
            template = template.replace('"', "'")

        return template

    def makeAspectGridOnlySVG(self, minify: bool = False, remove_css_variables = False):
        """
        Generate and save aspect-grid-only chart SVG to disk.

        Calls makeAspectGridOnlyTemplate and writes a file named
        "{subject.name} - {chart_type} Chart - Aspect Grid Only.svg" in the output directory.

        Args:
            minify (bool): Pass-through to makeAspectGridOnlyTemplate for compact output.
            remove_css_variables (bool): Pass-through to makeAspectGridOnlyTemplate to embed CSS variables.

        Returns:
            None
        """

        template = self.makeAspectGridOnlyTemplate(minify, remove_css_variables)
        chartname = self.output_directory / f"{self.user.name} - {self.chart_type} Chart - Aspect Grid Only.svg"

        with open(chartname, "w", encoding="utf-8", errors="ignore") as output_file:
            output_file.write(template)

        print(f"SVG Generated Correctly in: {chartname}")

if __name__ == "__main__":
    from kerykeion.utilities import setup_logging
    from kerykeion.composite_subject_factory import CompositeSubjectFactory
    setup_logging(level="debug")

    first = AstrologicalSubject("John Lennon", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    second = AstrologicalSubject("Paul McCartney", 1942, 6, 18, 15, 30, "Liverpool", "GB")

    # Internal Natal Chart
    internal_natal_chart = KerykeionChartSVG(first)
    internal_natal_chart.makeSVG()

    # External Natal Chart
    external_natal_chart = KerykeionChartSVG(first, "ExternalNatal", second)
    external_natal_chart.makeSVG()

    # Synastry Chart
    synastry_chart = KerykeionChartSVG(first, "Synastry", second)
    synastry_chart.makeSVG()

    # Transits Chart
    transits_chart = KerykeionChartSVG(first, "Transit", second)
    transits_chart.makeSVG()

    # Sidereal Birth Chart (Lahiri)
    sidereal_subject = AstrologicalSubject("John Lennon Lahiri", 1940, 10, 9, 18, 30, "Liverpool", "GB", zodiac_type="Sidereal", sidereal_mode="LAHIRI")
    sidereal_chart = KerykeionChartSVG(sidereal_subject)
    sidereal_chart.makeSVG()

    # Sidereal Birth Chart (Fagan-Bradley)
    sidereal_subject = AstrologicalSubject("John Lennon Fagan-Bradley", 1940, 10, 9, 18, 30, "Liverpool", "GB", zodiac_type="Sidereal", sidereal_mode="FAGAN_BRADLEY")
    sidereal_chart = KerykeionChartSVG(sidereal_subject)
    sidereal_chart.makeSVG()

    # Sidereal Birth Chart (DeLuce)
    sidereal_subject = AstrologicalSubject("John Lennon DeLuce", 1940, 10, 9, 18, 30, "Liverpool", "GB", zodiac_type="Sidereal", sidereal_mode="DELUCE")
    sidereal_chart = KerykeionChartSVG(sidereal_subject)
    sidereal_chart.makeSVG()

    # Sidereal Birth Chart (J2000)
    sidereal_subject = AstrologicalSubject("John Lennon J2000", 1940, 10, 9, 18, 30, "Liverpool", "GB", zodiac_type="Sidereal", sidereal_mode="J2000")
    sidereal_chart = KerykeionChartSVG(sidereal_subject)
    sidereal_chart.makeSVG()

    # House System Morinus
    morinus_house_subject = AstrologicalSubject("John Lennon - House System Morinus", 1940, 10, 9, 18, 30, "Liverpool", "GB", houses_system_identifier="M")
    morinus_house_chart = KerykeionChartSVG(morinus_house_subject)
    morinus_house_chart.makeSVG()

    ## To check all the available house systems uncomment the following code:
    # from kerykeion.kr_types import HousesSystemIdentifier
    # from typing import get_args
    # for i in get_args(HousesSystemIdentifier):
    #     alternatives_house_subject = AstrologicalSubject(f"John Lennon - House System {i}", 1940, 10, 9, 18, 30, "Liverpool", "GB", houses_system=i)
    #     alternatives_house_chart = KerykeionChartSVG(alternatives_house_subject)
    #     alternatives_house_chart.makeSVG()

    # With True Geocentric Perspective
    true_geocentric_subject = AstrologicalSubject("John Lennon - True Geocentric", 1940, 10, 9, 18, 30, "Liverpool", "GB", perspective_type="True Geocentric")
    true_geocentric_chart = KerykeionChartSVG(true_geocentric_subject)
    true_geocentric_chart.makeSVG()

    # With Heliocentric Perspective
    heliocentric_subject = AstrologicalSubject("John Lennon - Heliocentric", 1940, 10, 9, 18, 30, "Liverpool", "GB", perspective_type="Heliocentric")
    heliocentric_chart = KerykeionChartSVG(heliocentric_subject)
    heliocentric_chart.makeSVG()

    # With Topocentric Perspective
    topocentric_subject = AstrologicalSubject("John Lennon - Topocentric", 1940, 10, 9, 18, 30, "Liverpool", "GB", perspective_type="Topocentric")
    topocentric_chart = KerykeionChartSVG(topocentric_subject)
    topocentric_chart.makeSVG()

    # Minified SVG
    minified_subject = AstrologicalSubject("John Lennon - Minified", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    minified_chart = KerykeionChartSVG(minified_subject)
    minified_chart.makeSVG(minify=True)

    # Dark Theme Natal Chart
    dark_theme_subject = AstrologicalSubject("John Lennon - Dark Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    dark_theme_natal_chart = KerykeionChartSVG(dark_theme_subject, theme="dark")
    dark_theme_natal_chart.makeSVG()

    # Dark High Contrast Theme Natal Chart
    dark_high_contrast_theme_subject = AstrologicalSubject("John Lennon - Dark High Contrast Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    dark_high_contrast_theme_natal_chart = KerykeionChartSVG(dark_high_contrast_theme_subject, theme="dark-high-contrast")
    dark_high_contrast_theme_natal_chart.makeSVG()

    # Light Theme Natal Chart
    light_theme_subject = AstrologicalSubject("John Lennon - Light Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    light_theme_natal_chart = KerykeionChartSVG(light_theme_subject, theme="light")
    light_theme_natal_chart.makeSVG()

    # Dark Theme External Natal Chart
    dark_theme_external_subject = AstrologicalSubject("John Lennon - Dark Theme External", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    dark_theme_external_chart = KerykeionChartSVG(dark_theme_external_subject, "ExternalNatal", second, theme="dark")
    dark_theme_external_chart.makeSVG()

    # Dark Theme Synastry Chart
    dark_theme_synastry_subject = AstrologicalSubject("John Lennon - DTS", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    dark_theme_synastry_chart = KerykeionChartSVG(dark_theme_synastry_subject, "Synastry", second, theme="dark")
    dark_theme_synastry_chart.makeSVG()

    # Wheel Natal Only Chart
    wheel_only_subject = AstrologicalSubject("John Lennon - Wheel Only", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    wheel_only_chart = KerykeionChartSVG(wheel_only_subject)
    wheel_only_chart.makeWheelOnlySVG()

    # Wheel External Natal Only Chart
    wheel_external_subject = AstrologicalSubject("John Lennon - Wheel External Only", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    wheel_external_chart = KerykeionChartSVG(wheel_external_subject, "ExternalNatal", second)
    wheel_external_chart.makeWheelOnlySVG()

    # Wheel Synastry Only Chart
    wheel_synastry_subject = AstrologicalSubject("John Lennon - Wheel Synastry Only", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    wheel_synastry_chart = KerykeionChartSVG(wheel_synastry_subject, "Synastry", second)
    wheel_synastry_chart.makeWheelOnlySVG()

    # Wheel Transit Only Chart
    wheel_transit_subject = AstrologicalSubject("John Lennon - Wheel Transit Only", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    wheel_transit_chart = KerykeionChartSVG(wheel_transit_subject, "Transit", second)
    wheel_transit_chart.makeWheelOnlySVG()

    # Wheel Sidereal Birth Chart (Lahiri) Dark Theme
    sidereal_dark_subject = AstrologicalSubject("John Lennon Lahiri - Dark Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB", zodiac_type="Sidereal", sidereal_mode="LAHIRI")
    sidereal_dark_chart = KerykeionChartSVG(sidereal_dark_subject, theme="dark")
    sidereal_dark_chart.makeWheelOnlySVG()

    # Wheel Sidereal Birth Chart (Fagan-Bradley) Light Theme
    sidereal_light_subject = AstrologicalSubject("John Lennon Fagan-Bradley - Light Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB", zodiac_type="Sidereal", sidereal_mode="FAGAN_BRADLEY")
    sidereal_light_chart = KerykeionChartSVG(sidereal_light_subject, theme="light")
    sidereal_light_chart.makeWheelOnlySVG()

    # Aspect Grid Only Natal Chart
    aspect_grid_only_subject = AstrologicalSubject("John Lennon - Aspect Grid Only", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    aspect_grid_only_chart = KerykeionChartSVG(aspect_grid_only_subject)
    aspect_grid_only_chart.makeAspectGridOnlySVG()

    # Aspect Grid Only Dark Theme Natal Chart
    aspect_grid_dark_subject = AstrologicalSubject("John Lennon - Aspect Grid Dark Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    aspect_grid_dark_chart = KerykeionChartSVG(aspect_grid_dark_subject, theme="dark")
    aspect_grid_dark_chart.makeAspectGridOnlySVG()

    # Aspect Grid Only Light Theme Natal Chart
    aspect_grid_light_subject = AstrologicalSubject("John Lennon - Aspect Grid Light Theme", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    aspect_grid_light_chart = KerykeionChartSVG(aspect_grid_light_subject, theme="light")
    aspect_grid_light_chart.makeAspectGridOnlySVG()

    # Synastry Chart Aspect Grid Only
    aspect_grid_synastry_subject = AstrologicalSubject("John Lennon - Aspect Grid Synastry", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    aspect_grid_synastry_chart = KerykeionChartSVG(aspect_grid_synastry_subject, "Synastry", second)
    aspect_grid_synastry_chart.makeAspectGridOnlySVG()

    # Transit Chart Aspect Grid Only
    aspect_grid_transit_subject = AstrologicalSubject("John Lennon - Aspect Grid Transit", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    aspect_grid_transit_chart = KerykeionChartSVG(aspect_grid_transit_subject, "Transit", second)
    aspect_grid_transit_chart.makeAspectGridOnlySVG()

    # Synastry Chart Aspect Grid Only Dark Theme
    aspect_grid_dark_synastry_subject = AstrologicalSubject("John Lennon - Aspect Grid Dark Synastry", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    aspect_grid_dark_synastry_chart = KerykeionChartSVG(aspect_grid_dark_synastry_subject, "Synastry", second, theme="dark")
    aspect_grid_dark_synastry_chart.makeAspectGridOnlySVG()

    # Synastry Chart With draw_transit_aspect_list table
    synastry_chart_with_table_list_subject = AstrologicalSubject("John Lennon - SCTWL", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    synastry_chart_with_table_list = KerykeionChartSVG(synastry_chart_with_table_list_subject, "Synastry", second, double_chart_aspect_grid_type="list", theme="dark")
    synastry_chart_with_table_list.makeSVG()

    # Transit Chart With draw_transit_aspect_grid table
    transit_chart_with_table_grid_subject = AstrologicalSubject("John Lennon - TCWTG", 1940, 10, 9, 18, 30, "Liverpool", "GB")
    transit_chart_with_table_grid = KerykeionChartSVG(transit_chart_with_table_grid_subject, "Transit", second, double_chart_aspect_grid_type="table", theme="dark")
    transit_chart_with_table_grid.makeSVG()

    # Chines Language Chart
    chinese_subject = AstrologicalSubject("Hua Chenyu", 1990, 2, 7, 12, 0, "Hunan", "CN")
    chinese_chart = KerykeionChartSVG(chinese_subject, chart_language="CN")
    chinese_chart.makeSVG()

    # French Language Chart
    french_subject = AstrologicalSubject("Jeanne Moreau", 1928, 1, 23, 10, 0, "Paris", "FR")
    french_chart = KerykeionChartSVG(french_subject, chart_language="FR")
    french_chart.makeSVG()

    # Spanish Language Chart
    spanish_subject = AstrologicalSubject("Antonio Banderas", 1960, 8, 10, 12, 0, "Malaga", "ES")
    spanish_chart = KerykeionChartSVG(spanish_subject, chart_language="ES")
    spanish_chart.makeSVG()

    # Portuguese Language Chart
    portuguese_subject = AstrologicalSubject("Cristiano Ronaldo", 1985, 2, 5, 5, 25, "Funchal", "PT")
    portuguese_chart = KerykeionChartSVG(portuguese_subject, chart_language="PT")
    portuguese_chart.makeSVG()

    # Italian Language Chart
    italian_subject = AstrologicalSubject("Sophia Loren", 1934, 9, 20, 2, 0, "Rome", "IT")
    italian_chart = KerykeionChartSVG(italian_subject, chart_language="IT")
    italian_chart.makeSVG()

    # Russian Language Chart
    russian_subject = AstrologicalSubject("Mikhail Bulgakov", 1891, 5, 15, 12, 0, "Kiev", "UA")
    russian_chart = KerykeionChartSVG(russian_subject, chart_language="RU")
    russian_chart.makeSVG()

    # Turkish Language Chart
    turkish_subject = AstrologicalSubject("Mehmet Oz", 1960, 6, 11, 12, 0, "Istanbul", "TR")
    turkish_chart = KerykeionChartSVG(turkish_subject, chart_language="TR")
    turkish_chart.makeSVG()

    # German Language Chart
    german_subject = AstrologicalSubject("Albert Einstein", 1879, 3, 14, 11, 30, "Ulm", "DE")
    german_chart = KerykeionChartSVG(german_subject, chart_language="DE")
    german_chart.makeSVG()

    # Hindi Language Chart
    hindi_subject = AstrologicalSubject("Amitabh Bachchan", 1942, 10, 11, 4, 0, "Allahabad", "IN")
    hindi_chart = KerykeionChartSVG(hindi_subject, chart_language="HI")
    hindi_chart.makeSVG()

    # Kanye West Natal Chart
    kanye_west_subject = AstrologicalSubject("Kanye", 1977, 6, 8, 8, 45, "Atlanta", "US")
    kanye_west_chart = KerykeionChartSVG(kanye_west_subject)
    kanye_west_chart.makeSVG()

    # Composite Chart
    angelina = AstrologicalSubject("Angelina Jolie", 1975, 6, 4, 9, 9, "Los Angeles", "US", lng=-118.15, lat=34.03, tz_str="America/Los_Angeles")
    brad = AstrologicalSubject("Brad Pitt", 1963, 12, 18, 6, 31, "Shawnee", "US", lng=-96.56, lat=35.20, tz_str="America/Chicago")

    composite_subject_factory = CompositeSubjectFactory(angelina, brad)
    composite_subject_model = composite_subject_factory.get_midpoint_composite_subject_model()
    composite_chart = KerykeionChartSVG(composite_subject_model, "Composite")
    composite_chart.makeSVG()
