$.ajax({
    url: '/api/products/', // Make sure this URL is correctly configured in Django's urls.py
    method: 'GET',
    dataType: 'json', // Expect a JSON response
    success: function(response) {
        console.log(response);
    
    },
})
