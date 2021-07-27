export interface RenderOptions {
    // If a field has no value, don't show that field at all
    omitEmpty?: boolean;

    // The field that should be used to display
    // an object's title in an array of objects
    primaryKey?: string;
}
