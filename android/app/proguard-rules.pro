# Keep kotlinx.serialization generated serializers
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**

-keepclassmembers class com.calibreweb.reader.** {
    *** Companion;
}
-keepclasseswithmembers class com.calibreweb.reader.** {
    kotlinx.serialization.KSerializer serializer(...);
}
