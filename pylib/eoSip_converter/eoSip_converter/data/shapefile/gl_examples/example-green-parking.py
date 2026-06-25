import json

from eoSip_converter.data.shapefile import shapefile

json_data = open('green-p-parking-2019.json')
data = json.load(json_data)

with shapefile.Writer("green-p-parking-2019", shapefile.POINT) as w:
    w.field("id")
    w.field("address")
    w.field("lat")
    w.field("lng")
    w.field("rate")
    w.field("rate_half_hour")
    w.field("carpark_type")
    w.field("carpark_type_str")
    w.field("capacity")
    w.field("max_height")
    w.field("payment_options")

    i = 0  # should be changed to ? while (i < len(data["carparks"]))
    while i < 243:
        w.point(float(data["carparks"][i]["lng"]), float(data["carparks"][i]["lat"]))
        w.record(data["carparks"][i]["id"], data["carparks"][i]["address"], data["carparks"][i]["lat"],
                 data["carparks"][i]["lng"], data["carparks"][i]["rate"], data["carparks"][i]["rate_half_hour"],
                 data["carparks"][i]["carpark_type"], data["carparks"][i]["carpark_type_str"],
                 data["carparks"][i]["max_height"], data["carparks"][i]["capacity"],
                 data["carparks"][i]["payment_options"],
                 data["carparks"][i]["rate_details"])
        i += 1

    with open("csvSHP.prj", "w") as prj:
        epsg = 'GEOGCS["WGS 84",'
        epsg += 'DATUM["WGS_1984",'
        epsg += 'SPHEROID["WGS 84",6378137,298.257223563]]'
        epsg += ',PRIMEM["Greenwich",0],'
        epsg += 'UNIT["degree",0.0174532925199433]]'
        prj.write(epsg)

json_data.close()
