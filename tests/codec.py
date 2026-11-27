"""The JSON and YAML codecs the tests share, the same ones production builds."""

from red_thread_core.codec import create_json_codec, create_yaml_codec
from red_thread_core.errors import MalformedDocumentError

JSON = create_json_codec()
YAML = create_yaml_codec()


def decode_json[T](text: str, shape: type[T]) -> T:
    decoded = JSON.decode(text, shape)
    assert not isinstance(decoded, MalformedDocumentError), decoded
    return decoded
