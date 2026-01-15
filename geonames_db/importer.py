from geonames_db.models import GeoNamesCity, Admin1Code, CountryInfo

def import_cities500(session, file_path):
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            session.add(
                GeoNamesCity(
                    geonameid=int(parts[0]),
                    name=parts[1],
                    asciiname=parts[2],
                    latitude=float(parts[4]),
                    longitude=float(parts[5]),
                    country_code=parts[8],
                    admin1_code=parts[10],
                    population=int(parts[14] or 0),
                    timezone=parts[17],
                )
            )
    session.commit()


def import_admin1(session, file_path):
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            code, name, ascii_name, *_ = line.strip().split("\t")
            session.add(Admin1Code(code=code, name=name, ascii_name=ascii_name))
    session.commit()


def import_countries(session, file_path):
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split("\t")
            session.add(CountryInfo(iso=parts[0], country=parts[4]))
    session.commit()
