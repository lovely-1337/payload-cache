from typing import Self

from pydantic import AliasChoices, BaseModel, Field, model_validator


class CliSettings(BaseModel):
    """Аргументы командной строки. Pydantic сам проверяет и приводит типы."""

    # В задании -h назначен и для --host, и для --help: это конфликт.
    # --help оставляем стандартным (-h), а для host берём -H. Решение описано в README.
    host: str = Field(
        "http://localhost:8000",
        validation_alias=AliasChoices("H", "host"),
        description="Server URL",
    )
    repeat: int = Field(
        1,
        ge=1,
        validation_alias=AliasChoices("r", "repeat"),
        description="Number of iterations",
    )
    input: str | None = Field(
        None,
        validation_alias=AliasChoices("i", "input"),
        description="Input JSON file, '-' for stdin",
    )
    # Поле называется json_data, а не json: имя json занято методом BaseModel.
    json_data: str | None = Field(
        None,
        validation_alias=AliasChoices("j", "json"),
        description="Input as a JSON string",
    )
    output: str = Field(
        "-",
        validation_alias=AliasChoices("o", "output"),
        description="Output file, '-' for stdout",
    )

    @model_validator(mode="after")
    def exactly_one_input(self) -> Self:
        # Источник данных должен быть однозначным: иначе непонятно, что отправлять.
        if (self.input is None) == (self.json_data is None):
            raise ValueError("provide exactly one of --input or --json")
        return self
