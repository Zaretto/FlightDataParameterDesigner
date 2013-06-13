// -----------------------------------------------------------------------------
// POLARIS Flight Data Parameter Tree
// Copyright © 2012, Flight Data Services Ltd.
// -----------------------------------------------------------------------------

/*jshint browser: true, es5: true, indent: 4, jquery: true, strict: true */
/*global $jit: true, tableToGrid: true */

(function ($, window, document, undefined) {
    'use strict';

// -----------------------------------------------------------------------------
// Developer
// -----------------------------------------------------------------------------

    $(function () {
        $('#parameter_select_submit').click(function () {
            
            $.ajax({
                url: '/generate_graph',
                dataType: 'json',
                data: {
                    parameters: $('#parameter_select').val(),
                    file_path: $('#parameter_select').data('file-path')
                },
                success: function (data, status, xhr) {
                    var placeholder = $("#placeholder");
                    
                    var options = {
                    
                            grid: { hoverable: true, 
                                clickable: true,
                                backgroundColor: { colors: ["#fff", "#eee"]}}
                       };
                    
                    var plot = $.plot(placeholder, data.data, options);
                    
                },
                type: 'POST'
            });
        });
        
        $('#code_run').click(function () {
            $('#error_box').hide();
            $.ajax({
                url: '/code_run',
                dataType: 'json',
                data: {
                    code: $('#code').val(),
                    hdf_name_1: $('#parameter_select_1').val(),
                    var_name_1: $('#parameter_name_1').val(),
                    hdf_name_2: $('#parameter_select_2').val(),
                    var_name_2: $('#parameter_name_2').val(),
                    hdf_name_3: $('#parameter_select_3').val(),
                    var_name_3: $('#parameter_name_3').val(),
                    file_path: $('#parameter_select_1').data('file-path')
                },
                success: function (data, status, xhr) {
                    if (data.error) {
                        $('#error').text(data.error);
                        $('#error_box').css('display', 'inline-block');
                        return;
                    }
                    var placeholder = $("#placeholder1");
                    
                    var options = {
                    
                            grid: { hoverable: true, 
                                clickable: true,
                                backgroundColor: { colors: ["#fff", "#eee"]}}
                       };
                    
                    var plot = $.plot(placeholder, data.data[0], options);
                    
                    if (data.data[1]) {
                    
                        var placeholder = $("#placeholder2");
                        
                        var options = {
                        
                                grid: { hoverable: true, 
                                    clickable: true,
                                    backgroundColor: { colors: ["#fff", "#eee"]}}
                           };
                        
                        var plot = $.plot(placeholder, data.data[1], options);
                    }
                    
                    
                    if (data.data[2]) {
                    
                    var placeholder = $("#placeholder3");
                    
                    var options = {
                    
                            grid: { hoverable: true, 
                                clickable: true,
                                backgroundColor: { colors: ["#fff", "#eee"]}}
                       };
                    
                    var plot = $.plot(placeholder, data.data[2], options);
                    }
                    
                    
                    if (data.data[3]) {
                    var placeholder = $("#placeholder4");
                    
                    var options = {
                    
                            grid: { hoverable: true, 
                                clickable: true,
                                backgroundColor: { colors: ["#fff", "#eee"]}}
                       };
                    
                    var plot = $.plot(placeholder, data.data[3], options);
                    }
                },
                type: 'POST'
            });
        });
    });

// -----------------------------------------------------------------------------

}(jQuery, window, document));

// -----------------------------------------------------------------------------
// vim:et:ft=javascript:nowrap:sts=4:sw=4:ts=4
