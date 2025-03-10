from src.typification.dtos.input import OptionsComponents, FormComponents, FormInputDTO
from src.wrappers.aws.dynamodb import DynamoDBWrapper


def test_create_item():
    table = "test-dynamodb"

    components = [
        FormComponents(
            **{
                "name": "email",
                "label": "Quin és el teu email?",
                "type": "EMAIL_FIELD",
                "initialValue": "",
                "required": True,
            }
        ),
        FormComponents(
            **{
                "name": "password",
                "label": "Crea una contrasenya segura",
                "type": "PASSWORD_FIELD",
                "initialValue": "",
                "required": True,
            }
        ),
        FormComponents(
            **{
                "name": "singleChoice",
                "label": "Quin és el teu gust de gelat preferit?",
                "type": "SINGLECHOICE",
                "initialValue": "",
                "options": [
                    OptionsComponents(**{"value": "vanilla", "label": "Vainilla"}),
                    OptionsComponents(**{"value": "chocolate", "label": "Xocolata"}),
                    OptionsComponents(**{"value": "pistatxo", "label": "Festuc"}),
                    OptionsComponents(**{"value": "mango", "label": "Mango"}),
                ],
                "required": True,
            }
        ),
        FormComponents(
            **{
                "name": "multipleChoice",
                "label": "Com vols que et contactem?",
                "type": "MULTIPLE_CHOICE",
                "initialValue": [],
                "options": [
                    OptionsComponents(**{"value": "sms", "label": "SMS"}),
                    OptionsComponents(
                        **{"value": "email", "label": "Correu electrònic"}
                    ),
                    OptionsComponents(**{"value": "mail", "label": "Correu postal"}),
                    OptionsComponents(**{"value": "smoke", "label": "Senyals de fum"}),
                ],
                "required": True,
            }
        ),
    ]

    form_data = FormInputDTO(
        **{
            "id": "1234",
            "components": components,
            "name": "Formulari de prova",
            "created_at": "2023-10-10T10:10:10.000Z",
            "updated_at": "2023-10-10T10:10:10.000Z",
        }
    )

    item = DynamoDBWrapper().create_item(table, form_data.dict(exclude_none=True))

    assert isinstance(item, bool)
