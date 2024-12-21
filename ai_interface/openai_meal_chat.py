from pydantic import BaseModel
from openai import OpenAI, OpenAIError
import base64
from ai_interface import config
import logging
import copy
from pathlib import Path

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.key)


model = "gpt-4o"
logger.info(f"Using model {model}")

system_prompt = (
    "You are a nutrition analysis assistant. "
    "The user provides a meal description. "
    "Consider the meal description and the attached immage, if they exist."
    "Give the meal a short name. "
    "Give one sentence for a simple, concise meal description. "
    "Make a reasonable estimation for the nutrition value of this meal. "
    "Use grams for the proteins, fats, carbohydrates. "
    "Use kcal for the energy value. "
    "Use grams for the total weight. "
    "Set the success flag to true. "
    "\n"
    "In case of an error, set all the fields to 0 or empty string, "
    "set the success flag to false, and fill the error_message field. "
    "Potential errors: "
    "given image is not an image of food, "
    "given description is not a description of food, "
    "image does not match the description, "
    "the request does not make sense, "
    "additional message does not make sense for the original estimate, "
    "other errors. "
    "\n"
    "The user may send additional messages with clarifications or corrections. "
    "In this case, the original image that you have received will be dropped. "
    "But the original output that you have responded with will be present. "
    "Use the information from the user's response to your first message. "
    "Update each estimate value, when there is a reason to update it. "
)


class MealDataOutputFormat(BaseModel):
    name: str
    description: str
    proteins: float
    fats: float
    carbohydrates: float
    energy: float
    total_weight: float
    success_flag: bool
    error_message: str

    # chatgpt does not allow defining default values in class definition
    @staticmethod
    def default(
        name="", description="",
        proteins=0, fats=0, carbohydrates=0,
        energy=0, total_weight=0,
        success_flag=False,
        error_message=""
    ):
        return MealDataOutputFormat(
            name=name, description=description,
            proteins=proteins, fats=fats, carbohydrates=carbohydrates,
            energy=energy, total_weight=total_weight,
            success_flag=success_flag,
            error_message=error_message
        )


class ImageData(BaseModel):
    image_b64_string: str
    extension: str

    def __init__(self, image_data, extension):
        if isinstance(image_data, bytes):
            image_b64_string = ImageData.encode_to_b64(image_data)
        elif Path(image_data).is_file():
            image_b64_string = ImageData.encode_to_b64(
                open(image_data, "rb").read()
            )
        else:
            image_b64_string = image_data

        super().__init__(
            image_b64_string=image_b64_string,
            extension=extension
        )

    @staticmethod
    def encode_to_b64(data):
        return base64.b64encode(data).decode("utf-8")


class AiResponse(BaseModel):
    meal_data: MealDataOutputFormat
    message_list: list


def get_initial_messages(description=None, image_data=None):
    system_message = {
        "role": "system",
        "content": system_prompt
    }

    user_message = {
        "role": "user",
        "content": []
    }

    if description is not None:
        user_message["content"].append(get_text_content(description))

    if image_data is not None:
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{image_data.extension};base64,{image_data.image_b64_string}",
                "detail": "low"
            }
        }
        user_message["content"].append(image_content)

    return [system_message, user_message]


def get_update_request_message(request):
    update_message = {
        "role": "user",
        "content": request
    }
    return update_message


def get_meal_estimate(description=None, image_data=None):
    if description is None and image_data is None:
        raise TypeError("Both description and image data are missing")
    messages = get_initial_messages(description, image_data)
    return get_ai_response(messages)


def update_meal_estimate(previous_ai_response: AiResponse, update_request):
    messages = remove_non_text_messages(previous_ai_response.message_list)
    update_request_message = get_update_request_message(update_request)
    messages.append(update_request_message)
    return get_ai_response(messages)


def get_ai_response(messages):
    messages = list(messages)
    try:
        completion = get_message_completion(messages)
    except OpenAIError as e:
        error_message = f"OpenAIError exception: {e}"
        logger.error(error_message)
        meal_data = MealDataOutputFormat.default(
            success_flag=False, error_message=error_message
        )
    else:
        meal_data = parse_completion(completion)
        assistant_message = get_assistant_message(completion)
        messages.append(assistant_message)
    return AiResponse(meal_data=meal_data, message_list=messages)


def parse_completion(completion):
    parsed_output = completion.choices[0].message.parsed
    if parsed_output is not None:
        return parsed_output
    else:
        refusal = completion.choices[0].message.refusal
        error_message = f"OpenAI parsing failed with the following message: {refusal}"
        logger.error(error_message)
        return MealDataOutputFormat.default(
            success_flag=False, error_message=error_message
        )


def get_assistant_message(completion):
    assistant_message = {
        "role": "assistant",
        "content": completion.choices[0].message.content
    }
    return assistant_message


def remove_non_text_messages(messages):
    new_messages = []
    for message in messages:
        message = copy.deepcopy(message)
        old_content = message.get("content", list())

        if isinstance(old_content, str):
            new_content = [get_text_content(old_content)]
        else:
            new_content = []
            for c in old_content:
                if isinstance(c, str):
                    new_content.append(get_text_content(c))
                elif c.get("type", "text") == "text":
                    new_content.append(c)

        message["content"] = new_content
        new_messages.append(message)

    return new_messages


def get_text_content(text):
    return {"type": "text", "text": text}


def get_message_completion(messages):
    print("get_message_completion, messages", messages)
    completion = client.beta.chat.completions.parse(
        response_format=MealDataOutputFormat,
        model=model,
        messages=messages
    )
    logger.info(f"openai request total token usage: {completion.usage.total_tokens}")
    return completion
