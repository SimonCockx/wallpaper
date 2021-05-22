import logging
from configparser import ConfigParser, SectionProxy
from configparser import Error as ConfigParserError
from enum import Enum, unique, auto
from typing import Any

from handler.imagesource import DirectorySource


@unique
class ConfigField(Enum):
    SOURCES = auto()
    HOR_RESOLUTION = auto()
    VER_RESOLUTION = auto()
    LABEL_SIZE = auto()
    RIGHT_LABEL_MARGIN = auto()
    BOTTOM_LABEL_MARGIN = auto()
    CHANGE_TIME = auto()
    WIDGET_SCALE = auto()


class ConfigError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class MissingOptionError(ConfigError):
    def __init__(self, section: str, option: str) -> None:
        super().__init__(f'No option named "{option}" in section "{section}"')
        self.section = section
        self.option = option


def parse_directory_source(sect: SectionProxy) -> DirectorySource:
    root_folder = sect.get('root_folder')
    if root_folder is None:
        raise MissingOptionError(sect.name, 'root_folder')
    return DirectorySource(sect.name, sect['root_folder'])


def write_directory_source(sect: SectionProxy, s: DirectorySource) -> None:
    sect['root_folder'] = s.root_folder


class ConfigManager:
    basic_fields_title = 'config'
    basic_field_names = {
        ConfigField.HOR_RESOLUTION: 'horizontal_resolution',
        ConfigField.VER_RESOLUTION: 'vertical_resolution',
        ConfigField.LABEL_SIZE: 'label_size',
        ConfigField.RIGHT_LABEL_MARGIN: 'right_label_margin_pixels',
        ConfigField.BOTTOM_LABEL_MARGIN: 'bottom_label_margin_pixels',
        ConfigField.CHANGE_TIME: 'seconds_per_transition',
        ConfigField.WIDGET_SCALE: 'widget_scale',
    }
    basic_field_parsers = {
        ConfigField.HOR_RESOLUTION: int,
        ConfigField.VER_RESOLUTION: int,
        ConfigField.LABEL_SIZE: float,
        ConfigField.RIGHT_LABEL_MARGIN: int,
        ConfigField.BOTTOM_LABEL_MARGIN: int,
        ConfigField.CHANGE_TIME: float,
        ConfigField.WIDGET_SCALE: float,
    }
    basic_field_serializers = {
        ConfigField.HOR_RESOLUTION: str,
        ConfigField.VER_RESOLUTION: str,
        ConfigField.LABEL_SIZE: str,
        ConfigField.RIGHT_LABEL_MARGIN: str,
        ConfigField.BOTTOM_LABEL_MARGIN: str,
        ConfigField.CHANGE_TIME: str,
        ConfigField.WIDGET_SCALE: str,
    }
    source_parsers = {
        DirectorySource.type_name: parse_directory_source
    }
    source_writers = {
        DirectorySource.type_name: write_directory_source
    }

    def __init__(self) -> None:
        # Set defaults:
        self._values = {
            ConfigField.SOURCES: [],
            ConfigField.HOR_RESOLUTION: 1920,
            ConfigField.VER_RESOLUTION: 1080,
            ConfigField.LABEL_SIZE: 30.0,
            ConfigField.RIGHT_LABEL_MARGIN: 20,
            ConfigField.BOTTOM_LABEL_MARGIN: 60,
            ConfigField.CHANGE_TIME: 30.0,
            ConfigField.WIDGET_SCALE: 1.0,
        }

    def get_value(self, field: ConfigField) -> Any:
        return self._values.get(field)

    def set_value(self, field: ConfigField, value: Any) -> None:
        self._values[field] = value

    def read(self, config_path: str) -> list[ConfigField]:
        changed = []

        # Read config file
        config = ConfigParser()
        try:
            with open(config_path, 'r') as configfile:
                try:
                    config.read_file(configfile)
                except ConfigParserError as e:
                    raise ConfigError('Invalid configuration format') from e
        except IOError:
            logging.info(f'No configuration file found at {config_path}. Creating a new one.')
            self.write(config_path)
            return changed

        # Read basic fields
        if self.basic_fields_title not in config:
            raise ConfigError(f'No section named "{self.basic_fields_title}"')
        sec = config[self.basic_fields_title]
        for field, name in self.basic_field_names.items():
            if name not in sec:
                raise MissingOptionError(self.basic_fields_title, name)
            try:
                new = self.basic_field_parsers[field](sec[name])
            except ValueError as e:
                raise ConfigError(
                    f'Option "{name}" in section "{self.basic_fields_title}" has an invalid format') from e
            old = self.get_value(field)
            self._values[field] = new
            if old != new:
                changed.append(field)

        # Read sources
        new_sources = []
        for sec_title in config.sections():
            if sec_title == self.basic_fields_title:
                continue
            sec = config[sec_title]
            if 'type' not in sec:
                raise MissingOptionError(sec_title, 'type')
            t = sec['type']
            if t not in self.source_parsers:
                raise ConfigError(f'Invalid source type "{t}" in section "{sec_title}". '
                                  f'Possible types are {", ".join(self.source_parsers.keys())}')
            new_sources.append(self.source_parsers[t](sec))
        old_sources = self.get_value(ConfigField.SOURCES)
        self._values[ConfigField.SOURCES] = new_sources
        if new_sources != old_sources:
            changed.append(ConfigField.SOURCES)
        return changed

    def write(self, config_path: str) -> None:
        config = ConfigParser()
        config.add_section(self.basic_fields_title)
        for field, name in self.basic_field_names.items():
            config.set(self.basic_fields_title, name, self.basic_field_serializers[field](self.get_value(field)))

        for s in self.get_value(ConfigField.SOURCES):
            config.add_section(s.name)
            sec = config[s.name]
            sec['type'] = s.type_name
            self.source_writers[s.type_name](sec, s)

        with open(config_path, 'w') as configfile:
            config.write(configfile)
