'use strict';
{
    const $ = django.jQuery;

    // The API answers on the `Event` column names, which are the admin field ids.
    const GEOCODED_FIELDS = [
        'poi_name', 'address', 'postal_code', 'city',
        'cog_code', 'longitude', 'latitude', 'ban_id'
    ];

    $(function() {
        const search = $('#id_address_search');
        search.select2({
            theme: 'admin-autocomplete',
            language: 'fr',
            placeholder: 'Rechercher une adresse ou un lieu…',
            minimumInputLength: 3,
            ajax: {
                url: search.attr('data-ajax-url'),
                dataType: 'json',
                delay: 300,
                data: (params) => ({q: params.term})
            }
        });
        search.on('select2:select', (event) => {
            GEOCODED_FIELDS.forEach((name) => {
                document.getElementById('id_' + name).value = event.params.data[name] ?? '';
            });
        });
    });
}
