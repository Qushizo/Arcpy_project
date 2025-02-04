import arcpy
from arcpy.sa import *

# Ścieżki do danych wejściowych
arcpy.env.workspace = r"D:\Studia\rok_3\Zaliczenie_arcpy\temp"
arcpy.env.cellSize = "10"

dem = r"D:\Studia\rok_3\Zaliczenie_arcpy\Dane_testowe\dem10.tif"
ppwg = r"D:\Studia\rok_3\Zaliczenie_arcpy\Dane_testowe\ppwg.shp"
budynki = r"D:\Studia\rok_3\Zaliczenie_arcpy\Dane_testowe\OT_BUDB_A.shp"
obszar_prac = r"D:\Studia\rok_3\Zaliczenie_arcpy\Dane_testowe\Granica_Lublin.shp"
ujecia_wody = r"D:\Studia\rok_3\Zaliczenie_arcpy\Dane_testowe\Ujecia_wody.shp"

# Funkcja sprawdzająca, czy pole istnieje
def check_and_add_field(feature_class, field_name, field_type):
    fields = [f.name for f in arcpy.ListFields(feature_class)]
    if field_name not in fields:
        arcpy.AddField_management(feature_class, field_name, field_type)

# Obliczanie nachylenia terenu (slope) i rekalsyfikacja
slope_raster = Slope(dem)
nachylenia_dem = Reclassify(slope_raster, "Value", RemapRange([[0, 3, 1], [3, 90, 0]]))
nachylenia_dem.save("nachylenia.tif")

# Dodanie kolumny, przypisanie wartości w warstwie SHP i tworzenie rastra
check_and_add_field(ppwg, "Value", "SHORT")
with arcpy.da.UpdateCursor(ppwg, ["opis", "Value"]) as cursor:
    for row in cursor:
        row[1] = 1 if row[0] == "suche" else 0
        cursor.updateRow(row)
ppwg_raster = "ppwg_raster.tif"
arcpy.PolygonToRaster_conversion(ppwg, "Value", ppwg_raster)

# Tworzenie bufora 500m i dissolve dla drugiej warstwy SHP
ujecia_buffer = "ujecia_buffer.shp"
arcpy.Buffer_analysis(ujecia_wody, ujecia_buffer, "500 Meters")
ujecia_buffer_dissolve = "ujecia_dissolve.shp"
arcpy.Dissolve_management(ujecia_buffer, ujecia_buffer_dissolve)
check_and_add_field(ujecia_buffer_dissolve, "Value", "SHORT")
arcpy.CalculateField_management(ujecia_buffer_dissolve, "Value", 0)

# Dodanie kolumny do granicy miasta i ustawienie wartości 1
check_and_add_field(obszar_prac, "Value", "SHORT")
arcpy.CalculateField_management(obszar_prac, "Value", 1)
obszar_prac_raster = "obszar_prac.tif"
arcpy.PolygonToRaster_conversion(obszar_prac, "Value", obszar_prac_raster)

# Union warstw i konwersja na raster
#union_ujecia_obszar = "union_ujecia_obszar.shp"
#arcpy.Union_analysis([obszar_prac, ujecia_buffer_dissolve], union_ujecia_obszar)
erase_ujecia = "obszar_prac_ujecia_erased.shp"
arcpy.Erase_analysis(obszar_prac, ujecia_buffer_dissolve, erase_ujecia)
merge_ujecia_obszar = "merge_ujecia_obszar.shp"
arcpy.management.Merge([erase_ujecia, ujecia_buffer_dissolve], merge_ujecia_obszar)
ujecia_raster = "ujecia_raster.tif"
arcpy.PolygonToRaster_conversion(merge_ujecia_obszar, "Value", ujecia_raster)

# Filtrowanie budynków po wartościach X_KOD
budynki_wybrane = "budynki_wybrane.shp"
query = "\"X_KOD\" IN ('BUBD01', 'BUBD02', 'BUBD03', 'BUBD04', 'BUBD11')"
arcpy.Select_analysis(budynki, budynki_wybrane, query)

# Buforowanie wybranych budynków i dissolve
budynki_m_buffer = "budynki_m_buffer.shp"
arcpy.Buffer_analysis(budynki_wybrane, budynki_m_buffer, "50 Meters")
budynki_m_buffer_disolve = "budynki_m_buffer_disolve.shp"
arcpy.Dissolve_management(budynki_m_buffer, budynki_m_buffer_disolve)
check_and_add_field(budynki_m_buffer_disolve, "Value", "SHORT")
arcpy.CalculateField_management(budynki_m_buffer_disolve, "Value", 0)

# Union z granicą miasta i konwersja do rastra
#union_budynki_obszar = "union_budynki_obszar.shp"
#arcpy.Union_analysis([obszar_prac, budynki_m_buffer_disolve], union_budynki_obszar)
erase_budynki = "obszar_prac_budynki_erased.shp"
arcpy.Erase_analysis(obszar_prac, budynki_m_buffer_disolve, erase_budynki)
merge_budynki_obszar = "merge_budynki_obszar.shp"
arcpy.management.Merge([erase_budynki, budynki_m_buffer_disolve], merge_budynki_obszar)
budynki_m_raster = "budynki_m_raster.tif"
arcpy.PolygonToRaster_conversion(merge_budynki_obszar, "Value", budynki_m_raster)

# Sumowanie wszystkich rastrów
suma_raster = "suma_raster.tif"
raster1 = arcpy.Raster(ujecia_raster)
raster2 = arcpy.Raster(budynki_m_raster)
raster3 = arcpy.Raster(nachylenia_dem)
raster4 = arcpy.Raster(ppwg_raster)

final_raster = RasterCalculator(
    expression="r1 + r2 + r3 + r4",  
    rasters=[raster1, raster2, raster3, raster4],  
    input_names=["r1", "r2", "r3", "r4"]  
)
final_raster.save(suma_raster)
wynik_raster = Reclassify(suma_raster, "Value", RemapRange([[0, 3, 0], [3, 4, 1]]))
wynik_raster.save("raster_wynikowy.tif")

print("Proces zakończony pomyślnie!")
