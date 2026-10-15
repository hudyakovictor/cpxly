"""S-03 synthetic pilot. Deterministic facts and an explicitly unreviewed draft.
No legal interest, statutory deadlines or citations are invented here.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

VERSION = "s03-draft-v1"
REQUIRED = ("creditor", "debtor", "contract_number", "contract_date", "due_date", "amount", "description")


class InvalidClaim(ValueError):
    pass


def normalize(raw):
    result = {}
    for key in REQUIRED:
        value = str(raw.get(key, "")).strip()
        if not value or len(value) > (4000 if key == "description" else 200):
            raise InvalidClaim(f"Проверьте обязательное поле: {key}")
        if any(ord(c) < 32 and c not in "\n\t\r" for c in value):
            raise InvalidClaim("Недопустимые управляющие символы")
        result[key] = value
    for key in ("contract_date", "due_date"):
        try:
            result[key] = date.fromisoformat(result[key]).isoformat()
        except ValueError as exc:
            raise InvalidClaim("Дата должна быть действительной датой YYYY-MM-DD") from exc
    try:
        value = result["amount"].replace(" ", "").replace("\u00a0", "").replace(",", ".")
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000000"):
            raise InvalidClaim("Сумма должна быть положительной и в пределах лимита")
        if amount != amount.quantize(Decimal("0.01")):
            raise InvalidClaim("Не более двух знаков после запятой")
        result["amount"] = format(amount, ".2f")
    except (InvalidOperation, ValueError) as exc:
        raise InvalidClaim("Проверьте сумму") from exc
    if raw.get("facts_confirmed") is not True:
        raise InvalidClaim("Подтвердите введённые сведения")
    if raw.get("synthetic_data") is not True:
        raise InvalidClaim("Пилот принимает только синтетические данные")
    result["facts_confirmed"] = True
    result["synthetic_data"] = True
    return result


def build_draft(raw):
    data = normalize(raw)
    return "\n\n".join([
        "ПРОЕКТ ПРЕТЕНЗИИ ОБ ОПЛАТЕ",
        "СИНТЕТИЧЕСКИЙ ПИЛОТ. НЕ ПОДПИСАНО И НЕ ОТПРАВЛЕНО. НУЖНА ПРАВОВАЯ ПРОВЕРКА.",
        f"От: {data['creditor']}\nКому: {data['debtor']}",
        f"Основание по данным пользователя: договор № {data['contract_number']} от {data['contract_date']}.",
        f"Сведения об исполнении: {data['description']}",
        f"По введённым сведениям неоплаченная сумма составляет {data['amount']} руб. "
        f"Указанная пользователем дата оплаты: {data['due_date']}.",
        "Просим проверить расчёты по указанному обязательству и исполнить подтверждённое денежное обязательство. "
        "При наличии разногласий просим направить мотивированный ответ с подтверждающими документами.",
        "Перед использованием: сверить основание долга, факт и объём исполнения, оплату, реквизиты, полномочия, "
        "адресата, применимые сроки и условия договора; указать проверенный перечень приложений.",
        "Проценты, неустойка, срок ответа и правовые ссылки автоматически НЕ рассчитаны и НЕ подтверждены.",
        "Подпись уполномоченного лица: ____________________\nДата: ____________________",
    ])


def to_docx(text):
    """Minimal valid OOXML, no macros/external links; XML escaped, Arial 11pt."""
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraphs = "".join(
        '<w:p><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/>'
        '</w:rPr><w:t xml:space="preserve">' + escape(line) + '</w:t></w:r></w:p>'
        for line in text.split("\n")
    )
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{ns}"><w:body>{paragraphs}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
    content = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    result = BytesIO()
    with ZipFile(result, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return result.getvalue()
